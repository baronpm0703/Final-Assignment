from src.agents.data_agent import DataAgent
from src.infrastructure.sql_validator import SqlValidator
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter


class FakeDatabase:
    def __init__(self) -> None:
        self.sql: str | None = None
        self.validator = SqlValidator()

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


def make_agent(fake_db: FakeDatabase) -> DataAgent:
    return DataAgent(
        router=IntentRouter.default(),
        knowledge_service=KnowledgeService.from_markdown(),
        database=fake_db,
    )


def test_data_agent_answers_abandon_query() -> None:
    fake_db = FakeDatabase()
    response = make_agent(fake_db).answer("Phan tich abandon theo thang")

    assert response.type == "answer"
    assert response.visualization is not None
    assert response.visualization.type == "bar_chart"
    assert fake_db.sql is not None
    assert "abandon_sys" in fake_db.sql


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


def test_data_agent_accepts_memory_context() -> None:
    response = make_agent(FakeDatabase()).answer(
        "Phan tich abandon",
        memory_context="[Recent]\nuser: Thang 3/2026",
    )

    assert response.type == "answer"
