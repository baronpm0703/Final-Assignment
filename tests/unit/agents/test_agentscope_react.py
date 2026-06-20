from agentscope.agent import Agent
from agentscope.message import Msg, TextBlock

from src.agents.agentscope_react import AgentScopeReActRunner, _extract_msg_text
from src.domain.config import get_domain_config
from src.domain.intent import Intent, IntentResult, Language
from src.infrastructure.llm.ports import ChatRequest, ChatResponse, ToolCall
from src.infrastructure.sql_validator import SqlValidator
from src.rag.knowledge_service import KnowledgeService


class FakeDatabase:
    def __init__(self) -> None:
        domain_config = get_domain_config()
        self.validator = SqlValidator(
            allowed_schema=domain_config.schema.allowed_schema,
            allowed_functions=domain_config.schema.allowed_function_set,
        )
        self.sql: str | None = None

    def execute_select(self, sql: str, parameters: dict[str, object] | None = None):
        self.validator.validate(sql)
        self.sql = sql
        return [{"month": "2026-01-01", "abandon_sys": 0.2}]


class FakeLlm:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []
        self.domain_config = get_domain_config()

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        if len(self.requests) == 1:
            return ChatResponse(
                content="",
                model=request.model,
                tool_calls=[
                    ToolCall(
                        name="retrieve_knowledge",
                        arguments={"query": self._user_question(request)},
                    )
                ],
            )
        if len(self.requests) == 2:
            return ChatResponse(
                content="",
                model=request.model,
                tool_calls=[
                    ToolCall(
                        name="execute_sql",
                        arguments={
                            "sql": self.domain_config.agent.offline_query_plans[0].sql
                        },
                    )
                ],
            )
        return ChatResponse(content="done", model=request.model)

    def _user_question(self, request: ChatRequest) -> str:
        user_message = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        if "User question:" not in user_message:
            return user_message
        return user_message.split("User question:", 1)[1].split("\n\n", 1)[0].strip()


class RepeatingToolLlm:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            content="",
            model=request.model,
            tool_calls=[
                ToolCall(
                    name="retrieve_knowledge",
                    arguments={"query": "same query"},
                )
            ],
        )


def test_runner_uses_agentscope_framework() -> None:
    assert AgentScopeReActRunner.framework_name == "AgentScope"
    assert Agent.__module__.startswith("agentscope.")


def test_extract_msg_text_unwraps_text_block_repr() -> None:
    msg = Msg(
        name="assistant",
        role="assistant",
        content=[
            TextBlock(
                text=(
                    "[TextBlock(type='text', text='Tổng số cuộc gọi inbound là 2.800.', "
                    "id='77855555555555555555555555555555')]"
                )
            )
        ],
    )

    assert _extract_msg_text(msg) == "Tổng số cuộc gọi inbound là 2.800."


def test_extract_msg_text_normalizes_escaped_markdown_newlines() -> None:
    msg = Msg(
        name="assistant",
        role="assistant",
        content=[
            TextBlock(
                text=(
                    "Kết quả:\\n\\n- **Tháng 2/2026:** 12.96%\\n\\n"
                    "```sql\\nSELECT 1;\\n```"
                )
            )
        ],
    )

    assert _extract_msg_text(msg) == (
        "Kết quả:\n\n- **Tháng 2/2026:** 12.96%\n\n```sql\nSELECT 1;\n```"
    )


def test_runner_executes_agentscope_react_tools() -> None:
    database = FakeDatabase()
    domain_config = get_domain_config()
    runner = AgentScopeReActRunner(
        llm=FakeLlm(),
        llm_model="openai:gpt-4o-mini",
        knowledge_service=KnowledgeService.from_markdown(domain_config.knowledge.root_path),
        database=database,
        domain_config=domain_config,
        max_iters=6,
    )

    result = runner.run(
        message="Phan tich abandon theo thang",
        route=IntentResult(
            intent=Intent.DATA_QUERY,
            language=Language.VI,
            confidence=0.9,
            reason="test",
        ),
        memory_context=None,
    )

    assert database.sql is not None
    assert result.sql_executed == database.sql
    assert any("Action: retrieve_knowledge" in step for step in result.reasoning_steps)
    assert any("Action: execute_sql" in step for step in result.reasoning_steps)


def test_runner_stops_repeated_tool_call_loop() -> None:
    database = FakeDatabase()
    domain_config = get_domain_config()
    llm = RepeatingToolLlm()
    runner = AgentScopeReActRunner(
        llm=llm,
        llm_model="openai:gpt-4o-mini",
        knowledge_service=KnowledgeService.from_markdown(domain_config.knowledge.root_path),
        database=database,
        domain_config=domain_config,
        max_iters=6,
        max_repeated_tool_calls=1,
    )

    result = runner.run(
        message="Phan tich abandon theo thang",
        route=IntentResult(
            intent=Intent.DATA_QUERY,
            language=Language.VI,
            confidence=0.9,
            reason="test",
        ),
        memory_context=None,
    )

    assert len(llm.requests) == 2
    assert database.sql is None
    assert any("Stopped reason: repeated_tool_call" in step for step in result.reasoning_steps)
