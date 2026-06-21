import json
from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.core.config import Settings
from src.domain.intent import Language
from src.domain.response import AgentResponse
from src.memory.conversation_memory import ConversationMemory, ConversationMessage
from src.memory.conversation_store import ConversationSummary


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


class FakeConversationStore:
    def __init__(self, messages: dict[str, list[ConversationMessage]] | None = None) -> None:
        self.messages = messages or {}

    def create_conversation(self, conversation_id: str) -> None:
        self.messages.setdefault(conversation_id, [])

    def list_conversations(self) -> list[ConversationSummary]:
        return [
            ConversationSummary(
                conversation_id=conversation_id,
                created_at=messages[0].created_at if messages else datetime.now(UTC),
                updated_at=messages[-1].created_at if messages else datetime.now(UTC),
                message_count=len(messages),
                title=next(
                    (message.content[:80] for message in messages if message.role == "user"),
                    None,
                ),
            )
            for conversation_id, messages in self.messages.items()
        ]

    def exists(self, conversation_id: str) -> bool:
        return conversation_id in self.messages

    def get_messages(self, conversation_id: str) -> list[ConversationMessage]:
        return list(self.messages.get(conversation_id, []))

    def append_message(self, conversation_id: str, role: str, content: str) -> None:
        self.messages.setdefault(conversation_id, []).append(
            ConversationMessage(role=role, content=content)
        )

    def delete(self, conversation_id: str) -> bool:
        return self.messages.pop(conversation_id, None) is not None


def make_client(
    *,
    agent: FakeAgent | None = None,
    memory: ConversationMemory | None = None,
    conversation_store: FakeConversationStore | None = None,
) -> TestClient:
    app = create_app(
        Settings(app_env="test", llm_provider="openai", llm_model="openai:gpt-4o-mini"),
        agent=agent or FakeAgent(),  # type: ignore[arg-type]
        memory=memory or ConversationMemory(),
        conversation_store=conversation_store,  # type: ignore[arg-type]
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


def test_stream_chat_resumes_persisted_conversation_when_memory_is_empty() -> None:
    agent = FakeAgent()
    store = FakeConversationStore(
        {
            "old-session": [
                ConversationMessage(role="user", content="Old question"),
                ConversationMessage(role="assistant", content="Old answer"),
            ]
        }
    )
    client = make_client(agent=agent, conversation_store=store)

    response = client.post(
        "/api/chat/stream",
        json={"message": "Follow up question", "conversation_id": "old-session"},
    )

    assert response.status_code == 200
    assert len(agent.memory_contexts) == 1
    assert "user: Old question" in (agent.memory_contexts[0] or "")
    assert "assistant: Old answer" in (agent.memory_contexts[0] or "")
    assert "user: Follow up question" in (agent.memory_contexts[0] or "")
    assert [message.content for message in store.messages["old-session"]] == [
        "Old question",
        "Old answer",
        "Follow up question",
        "received: Follow up question",
    ]
