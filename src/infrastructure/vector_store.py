from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.rag.knowledge_service import KnowledgeChunk, RetrievedChunk


class PgVectorKnowledgeStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def upsert(self, chunks: Sequence[KnowledgeChunk]) -> None:
        with self.engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE kb_chunks"))
            for chunk in chunks:
                connection.execute(
                    text(
                        """
                        INSERT INTO kb_chunks (source, title, content, embedding)
                        VALUES (:source, :title, :content, :embedding)
                        """
                    ),
                    {
                        "source": chunk.source,
                        "title": chunk.title,
                        "content": chunk.content,
                        "embedding": chunk.embedding,
                    },
                )

    def search(self, query_embedding: list[float], *, limit: int = 5) -> list[RetrievedChunk]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT source, title, content, 1 - (embedding <=> :embedding) AS score
                    FROM kb_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding
                    LIMIT :limit
                    """
                ),
                {"embedding": query_embedding, "limit": limit},
            ).mappings()
            return [
                RetrievedChunk(
                    source=str(row["source"]),
                    title=str(row["title"]),
                    content=str(row["content"]),
                    score=float(row["score"]),
                )
                for row in rows
            ]
