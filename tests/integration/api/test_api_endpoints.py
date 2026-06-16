from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.config import Settings
from src.domain.intent import Language
from src.domain.response import AgentResponse
from src.memory.conversation_memory import ConversationMemory


class FakeAgent:
    def answer(self, message: str, *, memory_context: str | None = None) -> AgentResponse:
        return AgentResponse(
            type="answer",
            answer=f"received: {message}",
            language=Language.VI,
            reasoning_steps=["fake agent"],
        )


def make_client() -> TestClient:
    app = create_app(
        Settings(app_env="test", llm_provider="openai", llm_model="openai:gpt-4o-mini"),
        agent=FakeAgent(),  # type: ignore[arg-type]
        memory=ConversationMemory(),
    )
    return TestClient(app)


def test_health_endpoint() -> None:
    response = make_client().get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_config_endpoint() -> None:
    response = make_client().get("/api/config")

    assert response.status_code == 200
    assert response.json()["llm_model"] == "openai:gpt-4o-mini"


def test_chat_endpoint() -> None:
    response = make_client().post(
        "/api/chat",
        json={"message": "Phan tich abandon", "conversation_id": "c1"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "received: Phan tich abandon"
