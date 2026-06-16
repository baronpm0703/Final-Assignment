from agentscope.agent import Agent

from src.agents.agentscope_react import AgentScopeReActRunner
from src.agents.data_agent import DataAgent
from src.agents.prompts import load_data_agent_system_prompt
from src.domain.config import get_domain_config
from src.infrastructure.llm.ports import ChatRequest, ChatResponse, ToolCall
from src.infrastructure.sql_validator import SqlValidator
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter


class FakeDatabase:
    def __init__(self) -> None:
        self.sql: str | None = None
        domain_config = get_domain_config()
        self.validator = SqlValidator(
            allowed_schema=domain_config.schema.allowed_schema,
            allowed_functions=domain_config.schema.allowed_function_set,
        )

    def execute_select(self, sql: str, parameters: dict[str, object] | None = None):
        self.validator.validate(sql)
        self.sql = sql
        if "abandon_sys" in sql:
            return [
                {"month": "2026-01-01", "total_calls": 10, "abandoned_calls": 2, "abandon_sys": 0.2}
            ]
        if "request_name" in sql:
            return [{"request_name": "Card support", "request_count": 5, "share": 0.5}]
        if "handled_calls" in sql:
            return [{"agent_id": "AG001", "agent_name": "Nguyen Van An", "handled_calls": 12}]
        return []


class FakeLlm:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []
        self.domain_config = get_domain_config()

    def complete(self, request: ChatRequest) -> ChatResponse:
        self.requests.append(request)
        question = self._user_question(request)
        if len(self.requests) == 1:
            return ChatResponse(
                content="",
                model=request.model,
                tool_calls=[
                    ToolCall(name="retrieve_knowledge", arguments={"query": question})
                ],
            )

        if len(self.requests) == 2:
            if "tong dai" in question.lower():
                return ChatResponse(
                    content=(
                        "Bạn muốn phân tích nội dung nào? Vui lòng chọn hoặc mô tả rõ "
                        "metric, phạm vi, và khoảng thời gian."
                    ),
                    model=request.model,
                )
            if "cong thuc" in question.lower() or "la gi" in question.lower():
                return ChatResponse(
                    content="",
                    model=request.model,
                    tool_calls=[
                        ToolCall(
                            name="answer_business_question",
                            arguments={"question": question},
                        )
                    ],
                )
            sql = self._sql_for_question(question)
            return ChatResponse(
                content="",
                model=request.model,
                tool_calls=[ToolCall(name="execute_sql", arguments={"sql": sql})],
            )

        return ChatResponse(
            content="Use retrieved knowledge and validated SQL.",
            model=request.model,
        )

    def _user_question(self, request: ChatRequest) -> str:
        user_message = next(
            (message.content for message in reversed(request.messages) if message.role == "user"),
            "",
        )
        if "User question:" not in user_message:
            return user_message
        return user_message.split("User question:", 1)[1].split("\n\n", 1)[0].strip()

    def _sql_for_question(self, question: str) -> str:
        lowered = question.lower()
        for plan in self.domain_config.agent.offline_query_plans:
            if any(keyword.lower() in lowered for keyword in plan.match_keywords):
                return plan.sql
        return self.domain_config.agent.offline_query_plans[0].sql


def make_agent(fake_db: FakeDatabase, fake_llm: FakeLlm | None = None) -> DataAgent:
    fake_llm = fake_llm or FakeLlm()
    domain_config = get_domain_config()
    return DataAgent(
        router=IntentRouter.default(domain_config),
        knowledge_service=KnowledgeService.from_markdown(domain_config.knowledge.root_path),
        database=fake_db,
        llm=fake_llm,
        llm_model="openai:gpt-4o-mini",
        domain_config=domain_config,
    )


def test_data_agent_answers_abandon_query() -> None:
    fake_db = FakeDatabase()
    fake_llm = FakeLlm()
    response = make_agent(fake_db, fake_llm).answer("Phan tich abandon theo thang")

    assert response.type == "answer"
    assert response.visualization is not None
    assert response.visualization.type == "line_chart"
    assert fake_db.sql is not None
    assert "abandon_sys" in fake_db.sql
    assert any("AgentScope ReAct loop used" in step for step in response.reasoning_steps)
    assert any("Action: retrieve_knowledge" in step for step in response.reasoning_steps)
    assert any("Action: execute_sql" in step for step in response.reasoning_steps)


def test_data_agent_answers_request_mix_query() -> None:
    fake_db = FakeDatabase()
    response = make_agent(fake_db).answer("Hom qua cac cuoc goi den co yeu cau nao cao nhat")

    assert response.type == "answer"
    assert response.visualization is not None
    assert response.visualization.type == "pie_chart"


def test_data_agent_returns_out_of_scope() -> None:
    response = make_agent(FakeDatabase()).answer("Hom qua giai ngan bao nhieu hop dong")

    assert response.type == "out_of_scope"


def test_data_agent_returns_clarification_for_ambiguous_metric() -> None:
    response = make_agent(FakeDatabase()).answer("Cho toi xem thong ke tong dai")

    assert response.type == "clarification_needed"
    assert response.options


def test_data_agent_answers_business_knowledge_without_sql() -> None:
    fake_db = FakeDatabase()
    response = make_agent(fake_db).answer("Abandon_SYS la gi va cong thuc tinh nhu the nao")

    assert response.type == "answer"
    assert "Abandon_SYS" in response.answer
    assert response.sql_executed is None
    assert fake_db.sql is None
    assert any("Action: answer_business_question" in step for step in response.reasoning_steps)


def test_data_agent_accepts_memory_context() -> None:
    response = make_agent(FakeDatabase()).answer(
        "Phan tich abandon",
        memory_context="[Recent]\nuser: Thang 3/2026",
    )

    assert response.type == "answer"


def test_data_agent_system_prompt_file_is_required() -> None:
    prompt = load_data_agent_system_prompt()

    assert "Every SQL query must include an explicit LIMIT" in prompt


def test_agentscope_framework_is_the_react_runtime() -> None:
    assert AgentScopeReActRunner.framework_name == "AgentScope"
    assert Agent.__module__.startswith("agentscope.")
