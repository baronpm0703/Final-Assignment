import json
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.config import Settings
from src.domain.intent import Language
from src.domain.response import AgentResponse
from src.memory.conversation_memory import ConversationMemory


class FakeAgent:
    def __init__(self) -> None:
        self.memory_contexts: list[str | None] = []

    def answer(self, message: str, *, memory_context: str | None = None) -> AgentResponse:
        self.memory_contexts.append(memory_context)
        return AgentResponse(
            type="answer",
            answer=f"received: {message}",
            language=Language.VI,
            reasoning_steps=["fake agent"],
        )

    async def stream_answer(self, message: str, *, memory_context: str | None = None):
        self.memory_contexts.append(memory_context)
        yield {"type": "status", "message": "thinking"}
        yield {
            "type": "result",
            "answer": f"received: {message}",
            "reasoning_steps": ["fake stream"],
            "visualization": {
                "type": "line_chart",
                "title": "Fake chart",
                "data": [{"month": "2026-03", "value": Decimal("12.34")}],
            },
        }


def make_client(
    *, agent: FakeAgent | None = None, memory: ConversationMemory | None = None
) -> TestClient:
    app = create_app(
        Settings(app_env="test", llm_provider="openai", llm_model="openai:gpt-4o-mini"),
        agent=agent or FakeAgent(),  # type: ignore[arg-type]
        memory=memory or ConversationMemory(),
    )
    return TestClient(app)


def parse_sse_events(response) -> list[dict]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


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
    assert response.json()["conversation_id"] == "c1"


def test_stream_chat_returns_conversation_id_and_keeps_follow_up_context() -> None:
    agent = FakeAgent()
    client = make_client(agent=agent)

    first_response = client.post("/api/chat/stream", json={"message": "First question"})
    assert first_response.status_code == 200
    first_events = parse_sse_events(first_response)
    conversation_id = first_events[0]["conversation_id"]

    assert first_events[0] == {"type": "metadata", "conversation_id": conversation_id}
    assert first_events[-1]["conversation_id"] == conversation_id
    assert first_events[-1]["visualization"]["data"][0]["value"] == 12.34

    second_response = client.post(
        "/api/chat/stream",
        json={"message": "Follow up question", "conversation_id": conversation_id},
    )

    assert second_response.status_code == 200
    assert len(agent.memory_contexts) == 2
    assert "user: First question" in (agent.memory_contexts[1] or "")
    assert "assistant: received: First question" in (agent.memory_contexts[1] or "")
    assert "user: Follow up question" in (agent.memory_contexts[1] or "")


def test_stream_chat_keeps_default_follow_up_context_without_client_session_id() -> None:
    agent = FakeAgent()
    client = make_client(agent=agent)

    first_response = client.post("/api/chat/stream", json={"message": "First question"})
    second_response = client.post("/api/chat/stream", json={"message": "Follow up question"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert parse_sse_events(first_response)[0]["conversation_id"] == "default"
    assert parse_sse_events(second_response)[0]["conversation_id"] == "default"
    assert len(agent.memory_contexts) == 2
    assert "user: First question" in (agent.memory_contexts[1] or "")
    assert "assistant: received: First question" in (agent.memory_contexts[1] or "")
    assert "user: Follow up question" in (agent.memory_contexts[1] or "")
