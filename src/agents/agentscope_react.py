import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import CredentialBase
from agentscope.message import Msg, TextBlock, ToolCallBlock, ToolResultBlock, UserMsg
from agentscope.model import ChatModelBase
from agentscope.model import ChatResponse as AgentScopeChatResponse
from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.tool import FunctionTool, Toolkit
from pydantic import BaseModel

from src.agents.prompts import load_data_agent_system_prompt
from src.agents.tools import SqlExecutor
from src.domain.config import DomainConfig
from src.domain.intent import IntentResult
from src.infrastructure.llm.ports import (
    ChatCompletionPort,
    ChatMessage,
    ChatRequest,
)
from src.rag.knowledge_service import KnowledgeService, RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class AgentScopeRunResult:
    answer: str
    reasoning_steps: list[str]
    sql_executed: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    response_type: str = "answer"


@dataclass
class AgentScopeToolState:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    llm_calls: int = 0
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    sql_executed: str | None = None
    rows: list[dict[str, Any]] = field(default_factory=list)
    business_answer: str | None = None
    tool_trace: list[str] = field(default_factory=list)
    last_tool_signature: str | None = None
    repeated_tool_calls: int = 0
    stopped_reason: str | None = None


class AutoAllowFunctionTool(FunctionTool):
    async def check_permissions(self, *_args: Any, **_kwargs: Any) -> PermissionDecision:
        return PermissionDecision(
            behavior=PermissionBehavior.ALLOW,
            message="Read-only analytics tool is allowed.",
        )


class AgentScopeChatModel(ChatModelBase):
    class Parameters(BaseModel):
        pass

    def __init__(
        self,
        *,
        provider: ChatCompletionPort,
        model_id: str,
        state: AgentScopeToolState,
        max_repeated_tool_calls: int,
        context_size: int = 32768,
    ) -> None:
        super().__init__(
            credential=CredentialBase(),
            model=model_id,
            parameters=self.Parameters(),
            stream=False,
            max_retries=0,
            context_size=context_size,
        )
        self.provider = provider
        self.state = state
        self.max_repeated_tool_calls = max_repeated_tool_calls
        self._tool_call_index = 0

    async def _call_api(
        self,
        model_name: str,
        messages: list[Msg],
        tools: list[dict] | None = None,
        tool_choice: Any | None = None,
        **kwargs: Any,
    ) -> AgentScopeChatResponse:
        chat_messages = self._to_chat_messages(messages)
        self.state.llm_calls += 1
        logger.debug(
            "agentscope_llm_request",
            extra={
                "run_id": self.state.run_id,
                "llm_call": self.state.llm_calls,
                "model": model_name,
                "message_count": len(chat_messages),
                "last_message_role": chat_messages[-1].role if chat_messages else None,
                "last_message_preview": (
                    chat_messages[-1].content[:300] if chat_messages else None
                ),
                "tool_names": [
                    tool.get("function", {}).get("name") for tool in tools or []
                ],
            },
        )
        logger.debug(
            "agentscope_llm_request_full",
            extra={
                "run_id": self.state.run_id,
                "llm_call": self.state.llm_calls,
                "messages": [message.__dict__ for message in chat_messages],
                "tool_choice": tool_choice,
            },
        )
        response = self.provider.complete(
            ChatRequest(
                model=model_name,
                messages=chat_messages,
                temperature=float(kwargs.get("temperature", 0.0)),
                tools=tools or [],
            )
        )
        logger.debug(
            "agentscope_llm_response",
            extra={
                "run_id": self.state.run_id,
                "llm_call": self.state.llm_calls,
                "model": response.model,
                "has_content": bool(response.content),
                "content_preview": (response.content[:300] if response.content else None),
                "tool_calls": [
                    {"name": tc.name, "arguments": tc.arguments}
                    for tc in response.tool_calls
                ],
            },
        )
        logger.debug(
            "agentscope_llm_response_full",
            extra={
                "run_id": self.state.run_id,
                "llm_call": self.state.llm_calls,
                "content": response.content,
            },
        )
        if response.tool_calls:
            tool_signature = json.dumps(
                [
                    {"name": tool_call.name, "arguments": tool_call.arguments}
                    for tool_call in response.tool_calls
                ],
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
            if tool_signature == self.state.last_tool_signature:
                self.state.repeated_tool_calls += 1
            else:
                self.state.last_tool_signature = tool_signature
                self.state.repeated_tool_calls = 1

            if self.state.repeated_tool_calls > self.max_repeated_tool_calls:
                self.state.stopped_reason = (
                    "repeated_tool_call:"
                    f"{self.state.repeated_tool_calls}:{tool_signature[:500]}"
                )
                logger.warning(
                    "agent_repeated_tool_stopped",
                    extra={
                        "run_id": self.state.run_id,
                        "repeated_count": self.state.repeated_tool_calls,
                    },
                )
                return AgentScopeChatResponse(
                    content=[
                        TextBlock(
                            text=(
                                "Không thể hoàn tất vì agent đang gọi lặp lại cùng một "
                                "tool với cùng tham số. Vui lòng thử diễn đạt cụ thể hơn."
                            )
                        )
                    ],
                    is_last=True,
                )

            blocks: list[ToolCallBlock] = []
            for tool_call in response.tool_calls:
                self._tool_call_index += 1
                blocks.append(
                    ToolCallBlock(
                        id=f"tool_{self._tool_call_index}",
                        name=tool_call.name,
                        input=json.dumps(tool_call.arguments),
                    )
                )
            return AgentScopeChatResponse(
                content=blocks,
                is_last=True,
            )
        return AgentScopeChatResponse(
            content=[TextBlock(text=response.content)],
            is_last=True,
        )

    def _to_chat_messages(self, messages: list[Msg]) -> list[ChatMessage]:
        converted: list[ChatMessage] = []
        for message in messages:
            role = message.role
            if role not in {"system", "user", "assistant"}:
                role = "user"
            converted.append(ChatMessage(role=role, content=self._message_text(message)))
        return converted

    def _last_user_text(self, messages: list[Msg]) -> str:
        for message in reversed(messages):
            if message.role == "user":
                text = self._message_text(message)
                if "User question:" in text:
                    question_section = text.split("User question:", 1)[1]
                    return question_section.split("\n\n", 1)[0].strip()
                return text
        return ""

    def _message_text(self, message: Msg) -> str:
        chunks: list[str] = []
        for block in message.content:
            if isinstance(block, TextBlock):
                chunks.append(block.text)
            elif isinstance(block, ToolResultBlock):
                chunks.append(str(block.output))
        return "\n".join(chunks)


class AgentScopeReActRunner:
    framework_name = "AgentScope"

    def __init__(
        self,
        *,
        llm: ChatCompletionPort,
        llm_model: str,
        knowledge_service: KnowledgeService,
        database: SqlExecutor,
        domain_config: DomainConfig,
        system_prompt: str | None = None,
        max_iters: int = 8,
        max_repeated_tool_calls: int = 2,
    ) -> None:
        self.llm = llm
        self.llm_model = llm_model
        self.knowledge_service = knowledge_service
        self.database = database
        self.domain_config = domain_config
        self.system_prompt = system_prompt or load_data_agent_system_prompt()
        self.max_iters = max_iters
        self.max_repeated_tool_calls = max_repeated_tool_calls

    def run(
        self,
        *,
        message: str,
        route: IntentResult,
        memory_context: str | None,
    ) -> AgentScopeRunResult:
        return asyncio.run(
            self._run_async(message=message, route=route, memory_context=memory_context)
        )

    async def _run_async(
        self,
        *,
        message: str,
        route: IntentResult,
        memory_context: str | None,
    ) -> AgentScopeRunResult:
        state = AgentScopeToolState()
        logger.info(
            "agent_start",
            extra={
                "run_id": state.run_id,
                "intent": route.intent.value,
                "language": route.language.value,
                "model": self.llm_model,
                "user_message": message,
            },
        )
        toolkit = Toolkit(
            tools=[
                AutoAllowFunctionTool(self._retrieve_knowledge_tool(state)),
                AutoAllowFunctionTool(self._execute_sql_tool(state)),
                AutoAllowFunctionTool(self._answer_business_question_tool(state)),
            ]
        )
        agent = Agent(
            name="domain_data_agent",
            system_prompt=self.system_prompt,
            model=AgentScopeChatModel(
                provider=self.llm,
                model_id=self.llm_model,
                state=state,
                max_repeated_tool_calls=self.max_repeated_tool_calls,
            ),
            toolkit=toolkit,
            react_config=ReActConfig(max_iters=self.max_iters),
        )
        prompt = self._build_user_prompt(message, route, memory_context)
        logger.debug(
            "agentscope_user_prompt",
            extra={"run_id": state.run_id, "prompt": prompt},
        )
        final_msg = await agent.reply(UserMsg("user", prompt))
        answer = final_msg.get_text_content() or "Không tạo được câu trả lời."

        response_type = (
            "clarification_needed" if answer.startswith("Bạn muốn phân tích") else "answer"
        )
        logger.info(
            "agent_end",
            extra={
                "run_id": state.run_id,
                "response_type": response_type,
                "llm_calls": state.llm_calls,
                "tool_trace": state.tool_trace,
                "row_count": len(state.rows),
                "stopped_reason": state.stopped_reason,
            },
        )
        return AgentScopeRunResult(
            answer=state.business_answer or answer,
            reasoning_steps=[
                (
                    "AgentScope ReAct loop used "
                    f"with max_iters={self.max_iters}, llm_calls={state.llm_calls}"
                ),
                *([f"Stopped reason: {state.stopped_reason}"] if state.stopped_reason else []),
                *state.tool_trace,
            ],
            sql_executed=state.sql_executed,
            rows=state.rows,
            retrieved_chunks=state.retrieved_chunks,
            response_type=response_type,
        )

    def _build_user_prompt(
        self,
        message: str,
        route: IntentResult,
        memory_context: str | None,
    ) -> str:
        return (
            f"Detected language: {route.language.value}\n"
            f"Intent: {route.intent.value}\n"
            f"Router reason: {route.reason}\n\n"
            f"Conversation memory:\n{memory_context or '(none)'}\n\n"
            f"User question:\n{message}\n\n"
            "Use the available tools in ReAct style. Retrieve knowledge before SQL. "
            "For pure business/schema/KPI-definition questions, answer from knowledge "
            "without executing SQL. For data questions, execute read-only SQL."
        )

    def _retrieve_knowledge_tool(self, state: AgentScopeToolState):
        def retrieve_knowledge(query: str) -> str:
            """Retrieve domain schema, metric, and business knowledge.

            Args:
                query: User question or focused retrieval query.
            """
            chunks = self.knowledge_service.retrieve(query, limit=5)
            state.retrieved_chunks = chunks
            state.tool_trace.append(
                f"Action: retrieve_knowledge | Observation: {len(chunks)} chunks"
            )
            logger.info(
                "tool_retrieve_knowledge",
                extra={
                    "run_id": state.run_id,
                    "query": query,
                    "chunk_count": len(chunks),
                },
            )
            return json.dumps(
                [
                    {
                        "source": chunk.source,
                        "title": chunk.title,
                        "content": chunk.content,
                        "score": chunk.score,
                    }
                    for chunk in chunks
                ],
                ensure_ascii=False,
            )

        return retrieve_knowledge

    def _execute_sql_tool(self, state: AgentScopeToolState):
        def execute_sql(sql: str) -> str:
            """Validate and execute a read-only PostgreSQL SELECT query.

            Args:
                sql: A single SELECT query with explicit LIMIT.
            """
            try:
                rows = self.database.execute_select(sql)
            except Exception as exc:
                state.tool_trace.append(f"Action: execute_sql | Observation: error {exc}")
                logger.warning(
                    "tool_execute_sql_error",
                    extra={
                        "run_id": state.run_id,
                        "error": str(exc),
                    },
                )
                return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)

            state.sql_executed = sql
            state.rows = rows
            state.tool_trace.append(f"Action: execute_sql | Observation: {len(rows)} rows")
            logger.info(
                "tool_execute_sql",
                extra={
                    "run_id": state.run_id,
                    "row_count": len(rows),
                },
            )
            return json.dumps({"ok": True, "rows": rows}, ensure_ascii=False, default=str)

        return execute_sql

    def _answer_business_question_tool(self, state: AgentScopeToolState):
        def answer_business_question(question: str) -> str:
            """Answer a domain business/schema/metric question from knowledge only.

            Args:
                question: Business, schema, process, or KPI-definition question.
            """
            chunks = state.retrieved_chunks or self.knowledge_service.retrieve(question, limit=5)
            state.retrieved_chunks = chunks
            answer = synthesize_answer_from_chunks(chunks)
            state.business_answer = answer
            state.tool_trace.append(
                "Action: answer_business_question | Observation: knowledge answer"
            )
            logger.info(
                "tool_answer_business",
                extra={
                    "run_id": state.run_id,
                    "chunk_count": len(chunks),
                },
            )
            return answer

        return answer_business_question


def synthesize_answer_from_chunks(chunks: list[RetrievedChunk]) -> str:
    if chunks:
        top = chunks[0]
        return f"Theo knowledge base ({top.title}), {top.content[:500]}"
    return "Tôi chưa tìm thấy knowledge phù hợp cho câu hỏi này."


def infer_visualization_from_rows(rows: list[dict[str, Any]]) -> tuple[str, str]:
    if not rows:
        return "table", "Ket qua truy van"

    columns = list(rows[0].keys())
    numeric_columns = [
        column for column in columns if all(_is_number(row.get(column)) for row in rows)
    ]
    text_columns = [column for column in columns if column not in numeric_columns]
    temporal_columns = [
        column
        for column in columns
        if any(token in column.lower() for token in ["date", "time", "month", "year", "created"])
    ]
    ratio_columns = [
        column
        for column in numeric_columns
        if any(token in column.lower() for token in ["rate", "ratio", "percent", "share"])
    ]

    if temporal_columns and numeric_columns:
        return "line_chart", "Time series"
    if text_columns and ratio_columns:
        return "pie_chart", "Distribution"
    if text_columns and numeric_columns:
        return "bar_chart", "Ranking"
    return "table", "Query result"


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)
