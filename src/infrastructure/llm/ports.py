from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatRequest:
    messages: list[ChatMessage]
    model: str
    temperature: float = 0.0
    tools: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ChatResponse:
    content: str
    model: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class ChatCompletionPort(Protocol):
    def complete(self, request: ChatRequest) -> ChatResponse:
        """Return one chat completion response."""
