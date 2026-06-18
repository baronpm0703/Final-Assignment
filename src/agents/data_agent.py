from typing import Any, AsyncGenerator

from src.agents.agentscope_react import (
    AgentScopeReActRunner,
    infer_visualization_from_rows,
)
from src.agents.prompts import load_data_agent_system_prompt
from src.agents.tools import SqlExecutor
from src.domain.config import DomainConfig
from src.domain.intent import Intent, Language
from src.domain.response import AgentResponse, Visualization
from src.infrastructure.llm.ports import ChatCompletionPort
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter
from src.utils.formatting import compact_table


class DataAgent:
    def __init__(
        self,
        *,
        router: IntentRouter,
        knowledge_service: KnowledgeService,
        database: SqlExecutor,
        llm: ChatCompletionPort,
        llm_model: str,
        domain_config: DomainConfig,
        system_prompt: str | None = None,
    ) -> None:
        self.router = router
        self.knowledge_service = knowledge_service
        self.database = database
        self.llm = llm
        self.llm_model = llm_model
        self.domain_config = domain_config
        self.system_prompt = system_prompt or load_data_agent_system_prompt()
        self.react_runner = AgentScopeReActRunner(
            llm=llm,
            llm_model=llm_model,
            knowledge_service=knowledge_service,
            database=database,
            domain_config=domain_config,
            system_prompt=self.system_prompt,
            max_iters=domain_config.agent.max_react_iters,
            max_repeated_tool_calls=domain_config.agent.max_repeated_tool_calls,
        )

    def answer(self, message: str, *, memory_context: str | None = None) -> AgentResponse:
        route = self.router.route(message)
        routing_step = f"Route intent: {route.intent.value} ({route.reason})"
        if route.intent == Intent.UNSAFE:
            return AgentResponse(
                type="unsafe",
                answer=self._localized(route.language, "Input khong an toan.", "Unsafe input."),
                language=route.language,
                reasoning_steps=[routing_step],
            )
        if route.intent == Intent.OUT_OF_SCOPE:
            return AgentResponse(
                type="out_of_scope",
                answer=self._localized(
                    route.language,
                    f"Cau hoi nay nam ngoai pham vi: {self.domain_config.domain.description}.",
                    f"This question is outside the configured domain: "
                    f"{self.domain_config.domain.description}.",
                ),
                language=route.language,
                reasoning_steps=[routing_step],
            )
        if route.intent == Intent.CHITCHAT:
            return AgentResponse(
                type="answer",
                answer=self._localized(
                    route.language,
                    f"Xin chao, toi co the ho tro: {self.domain_config.domain.description}.",
                    f"Hello, I can help with: {self.domain_config.domain.description}.",
                ),
                language=route.language,
                reasoning_steps=[routing_step],
            )

        react_result = self.react_runner.run(
            message=message,
            route=route,
            memory_context=memory_context,
        )

        if react_result.response_type == "clarification_needed":
            return AgentResponse(
                type="clarification_needed",
                answer=react_result.answer,
                language=route.language,
                reasoning_steps=[routing_step, *react_result.reasoning_steps],
                options=self.domain_config.response.clarification_options,
            )

        if react_result.sql_executed:
            visualization_type, title = infer_visualization_from_rows(react_result.rows)
            return AgentResponse(
                type="answer",
                answer=self._answer_text(route.language, react_result.rows),
                language=route.language,
                visualization=Visualization(
                    type=visualization_type,  # type: ignore[arg-type]
                    title=title,
                    data=react_result.rows,
                ),
                sql_executed=react_result.sql_executed.strip(),
                reasoning_steps=[routing_step, *react_result.reasoning_steps],
            )

        return AgentResponse(
            type="answer",
            answer=react_result.answer,
            language=route.language,
            reasoning_steps=[routing_step, *react_result.reasoning_steps],
        )

    async def stream_answer(
        self, message: str, *, memory_context: str | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream answer with status updates via SSE."""
        route = self.router.route(message)
        routing_step = f"Route intent: {route.intent.value} ({route.reason})"
        
        # Handle special intents (no streaming needed)
        if route.intent == Intent.UNSAFE:
            yield {
                "type": "result",
                "answer": self._localized(route.language, "Input khong an toan.", "Unsafe input."),
                "reasoning_steps": [routing_step],
            }
            return
        
        if route.intent == Intent.OUT_OF_SCOPE:
            yield {
                "type": "result",
                "answer": self._localized(
                    route.language,
                    f"Cau hoi nay nam ngoai pham vi: {self.domain_config.domain.description}.",
                    f"This question is outside the configured domain: {self.domain_config.domain.description}.",
                ),
                "reasoning_steps": [routing_step],
            }
            return
        
        if route.intent == Intent.CHITCHAT:
            yield {
                "type": "result",
                "answer": self._localized(
                    route.language,
                    f"Xin chao, toi co the ho tro: {self.domain_config.domain.description}.",
                    f"Hello, I can help with: {self.domain_config.domain.description}.",
                ),
                "reasoning_steps": [routing_step],
            }
            return
        
        # For data queries, stream with status updates
        async for event in self.react_runner.stream_run(
            message=message,
            route=route,
            memory_context=memory_context,
        ):
            # Stream status updates as-is
            if event.get("type") == "status":
                yield event
            # Process final result
            elif event.get("type") == "result":
                yield {
                    "type": "result",
                    "answer": event.get("answer"),
                    "sql_executed": event.get("sql_executed"),
                    "reasoning_steps": [routing_step, *event.get("reasoning_steps", [])],
                }

    def _answer_text(self, language: Language, rows: list[dict[str, Any]]) -> str:
        if not rows:
            return self._localized(language, "Khong co du lieu phu hop.", "No matching data found.")

        preview = compact_table(rows, max_rows=3)
        return self._localized(
            language,
            f"Truy van tra ve {len(rows)} dong. Ket qua dau tien:\n{preview}",
            f"Query returned {len(rows)} rows. First results:\n{preview}",
        )

    def _localized(self, language: Language, vi: str, en: str) -> str:
        return vi if language == Language.VI else en
