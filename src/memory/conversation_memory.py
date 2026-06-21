from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

MessageRole = Literal["user", "assistant", "system"]


@dataclass(frozen=True)
class ConversationMessage:
    role: MessageRole
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class MemoryContext:
    summary: str | None
    compacted_messages: list[ConversationMessage]
    recent_messages: list[ConversationMessage]

    def render(self) -> str:
        sections: list[str] = []
        if self.summary:
            sections.append(f"[Summary]\n{self.summary}")
        if self.compacted_messages:
            compacted = "\n".join(
                f"{message.role}: {message.content}" for message in self.compacted_messages
            )
            sections.append(f"[Compacted]\n{compacted}")
        if self.recent_messages:
            recent = "\n".join(
                f"{message.role}: {message.content}" for message in self.recent_messages
            )
            sections.append(f"[Recent]\n{recent}")
        return "\n\n".join(sections)


class ConversationMemory:
    def __init__(
        self,
        *,
        window_size: int = 6,
        compaction_ratio: float = 0.70,
        summary_ratio: float = 0.70,
    ) -> None:
        self.window_size = window_size
        self.compaction_ratio = compaction_ratio
        self.summary_ratio = summary_ratio
        self._messages: dict[str, list[ConversationMessage]] = {}
        self._summary_cache: dict[str, str] = {}

    def append(self, conversation_id: str, role: MessageRole, content: str) -> None:
        self._messages.setdefault(conversation_id, []).append(
            ConversationMessage(role=role, content=content)
        )

    def exists(self, conversation_id: str) -> bool:
        return conversation_id in self._messages

    def create(self, conversation_id: str) -> None:
        """Create an empty conversation slot. Idempotent."""
        self._messages.setdefault(conversation_id, [])

    def replace_messages(self, conversation_id: str, messages: list[ConversationMessage]) -> None:
        """Replace runtime messages from persistent storage."""
        self._messages[conversation_id] = list(messages)
        self._summary_cache.pop(conversation_id, None)

    def list_conversations(self) -> list[str]:
        return list(self._messages.keys())

    def get_messages(self, conversation_id: str) -> list[ConversationMessage]:
        return list(self._messages.get(conversation_id, []))

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and its summary. Returns True if it existed."""
        existed = conversation_id in self._messages
        self._messages.pop(conversation_id, None)
        self._summary_cache.pop(conversation_id, None)
        return existed

    def build_context(self, conversation_id: str) -> MemoryContext:
        messages = self._messages.get(conversation_id, [])
        if len(messages) <= self.window_size:
            return MemoryContext(
                summary=self._summary_cache.get(conversation_id),
                compacted_messages=[],
                recent_messages=messages,
            )

        older = messages[: -self.window_size]
        recent = messages[-self.window_size :]
        compacted = [self._compact_message(message) for message in older]

        if self._should_summarize(compacted):
            self._summary_cache[conversation_id] = self._summarize(compacted)
            compacted = []

        return MemoryContext(
            summary=self._summary_cache.get(conversation_id),
            compacted_messages=compacted,
            recent_messages=recent,
        )

    def _compact_message(self, message: ConversationMessage) -> ConversationMessage:
        if message.role != "assistant":
            return message

        sentences = [
            sentence.strip() for sentence in message.content.split(".") if sentence.strip()
        ]
        compacted = ". ".join(sentences[:2])
        if compacted:
            compacted += "."
        return ConversationMessage(
            role=message.role,
            content=compacted or message.content[:240],
            created_at=message.created_at,
        )

    def _should_summarize(self, compacted: list[ConversationMessage]) -> bool:
        total_chars = sum(len(message.content) for message in compacted)
        threshold = max(1, int(self.window_size * 500 * self.summary_ratio))
        return total_chars > threshold

    def _summarize(self, messages: list[ConversationMessage]) -> str:
        user_turns = [message.content for message in messages if message.role == "user"]
        assistant_turns = [message.content for message in messages if message.role == "assistant"]
        summary_parts = []
        if user_turns:
            summary_parts.append(f"User asked: {'; '.join(user_turns[-3:])}")
        if assistant_turns:
            summary_parts.append(f"Assistant answered: {'; '.join(assistant_turns[-2:])}")
        return " ".join(summary_parts)[:1200]
