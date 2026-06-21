import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.memory.conversation_memory import ConversationMessage, MessageRole

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversationSummary:
    conversation_id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    title: str | None = None


class ConversationStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def ensure_schema(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id BIGSERIAL PRIMARY KEY,
                        conversation_id TEXT NOT NULL
                            REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                        content TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id, created_at, id)
                    """
                )
            )

    def create_conversation(self, conversation_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO conversations (conversation_id)
                    VALUES (:conversation_id)
                    ON CONFLICT (conversation_id) DO NOTHING
                    """
                ),
                {"conversation_id": conversation_id},
            )

    def list_conversations(self) -> list[ConversationSummary]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT
                        c.conversation_id,
                        c.created_at,
                        c.updated_at,
                        COUNT(m.id)::int AS message_count,
                        NULLIF(LEFT(first_user.content, 80), '') AS title
                    FROM conversations c
                    LEFT JOIN messages m ON m.conversation_id = c.conversation_id
                    LEFT JOIN LATERAL (
                        SELECT content
                        FROM messages
                        WHERE conversation_id = c.conversation_id
                            AND role = 'user'
                        ORDER BY created_at ASC, id ASC
                        LIMIT 1
                    ) first_user ON TRUE
                    GROUP BY c.conversation_id, c.created_at, c.updated_at, first_user.content
                    ORDER BY c.updated_at DESC, c.created_at DESC
                    """
                )
            ).mappings()
            return [
                ConversationSummary(
                    conversation_id=row["conversation_id"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    message_count=row["message_count"],
                    title=row["title"],
                )
                for row in rows
            ]

    def exists(self, conversation_id: str) -> bool:
        with self.engine.connect() as connection:
            return (
                connection.execute(
                    text(
                        """
                        SELECT 1
                        FROM conversations
                        WHERE conversation_id = :conversation_id
                        """
                    ),
                    {"conversation_id": conversation_id},
                ).first()
                is not None
            )

    def get_messages(self, conversation_id: str) -> list[ConversationMessage]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT role, content, created_at
                    FROM messages
                    WHERE conversation_id = :conversation_id
                    ORDER BY created_at ASC, id ASC
                    """
                ),
                {"conversation_id": conversation_id},
            ).mappings()
            return [
                ConversationMessage(
                    role=row["role"],
                    content=row["content"],
                    created_at=_coerce_utc(row["created_at"]),
                )
                for row in rows
            ]

    def append_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO conversations (conversation_id)
                    VALUES (:conversation_id)
                    ON CONFLICT (conversation_id)
                    DO UPDATE SET updated_at = now()
                    """
                ),
                {"conversation_id": conversation_id},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO messages (conversation_id, role, content)
                    VALUES (:conversation_id, :role, :content)
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                },
            )
            connection.execute(
                text(
                    """
                    UPDATE conversations
                    SET updated_at = now()
                    WHERE conversation_id = :conversation_id
                    """
                ),
                {"conversation_id": conversation_id},
            )

    def delete(self, conversation_id: str) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(
                text(
                    """
                    DELETE FROM conversations
                    WHERE conversation_id = :conversation_id
                    """
                ),
                {"conversation_id": conversation_id},
            )
            return (result.rowcount or 0) > 0


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
