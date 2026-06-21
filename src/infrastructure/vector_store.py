"""PgVector-backed knowledge store.

Stores chunk embeddings in a PostgreSQL table with the pgvector extension,
enabling efficient approximate nearest-neighbor (ANN) search via HNSW index.

Hybrid scoring: pgvector cosine distance + BM25 lexical scoring.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from rank_bm25 import BM25Okapi
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.rag.knowledge_service import KnowledgeChunk, RetrievedChunk

logger = logging.getLogger(__name__)


class PgVectorKnowledgeStore:
    """Knowledge store backed by PostgreSQL + pgvector.

    Table schema (created by scripts/sql/init.sql):
        kb_chunks (
            id          BIGSERIAL PRIMARY KEY,
            source      TEXT NOT NULL,
            title       TEXT NOT NULL,
            content     TEXT NOT NULL,
            embedding   VECTOR(1536) NOT NULL,
            created_at  TIMESTAMPTZ DEFAULT now()
        )

    Search strategy:
        1. pgvector cosine similarity fetches top-K candidates from the DB.
        2. BM25 re-scoring on the fetched candidates for hybrid ranking.
    """

    def __init__(self, engine: Engine, *, table_name: str = "kb_chunks") -> None:
        self.engine = engine
        self.table_name = table_name

    def upsert(self, chunks: Sequence[KnowledgeChunk]) -> int:
        """Replace all chunks in the table with new ones.

        Returns:
            Number of chunks inserted.
        """
        with self.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY"))
            for chunk in chunks:
                connection.execute(
                    text(f"""
                        INSERT INTO {self.table_name} (source, title, content, embedding)
                        VALUES (:source, :title, :content, :embedding)
                    """),
                    {
                        "source": chunk.source,
                        "title": chunk.title,
                        "content": chunk.content,
                        "embedding": str(chunk.embedding),
                    },
                )
        logger.info("Upserted %d chunks into '%s'", len(chunks), self.table_name)
        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        query: str = "",
        candidate_multiplier: int = 4,
    ) -> list[RetrievedChunk]:
        """Hybrid search: pgvector cosine + BM25 re-ranking.

        Args:
            query_embedding: Query vector.
            limit: Number of results to return.
            query: Raw query text for BM25 re-scoring.
            candidate_multiplier: Fetch N * limit candidates from pgvector
                                  before BM25 re-ranking.

        Returns:
            List of RetrievedChunk sorted by combined score.
        """
        fetch_limit = limit * candidate_multiplier

        with self.engine.connect() as connection:
            rows = connection.execute(
                text(f"""
                    SELECT source, title, content,
                           1 - (embedding <=> :embedding::vector) AS cosine_score
                    FROM {self.table_name}
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :fetch_limit
                """),
                {"embedding": str(query_embedding), "fetch_limit": fetch_limit},
            ).mappings().all()

        if not rows:
            return []

        candidates = [dict(row) for row in rows]

        # BM25 re-scoring
        bm25_scores = self._bm25_score(query, candidates)

        # Combine cosine + normalized BM25, re-rank
        results = [
            RetrievedChunk(
                source=str(c["source"]),
                title=str(c["title"]),
                content=str(c["content"]),
                score=float(c["cosine_score"]) + bm25,
            )
            for c, bm25 in zip(candidates, bm25_scores, strict=True)
        ]
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def count(self) -> int:
        """Return the number of chunks in the store."""
        with self.engine.connect() as connection:
            result = connection.execute(text(f"SELECT COUNT(*) FROM {self.table_name}"))
            return result.scalar() or 0

    def _bm25_score(self, query: str, candidates: list[dict]) -> list[float]:
        """Compute normalized BM25 scores for candidate chunks."""
        if not query.strip():
            return [0.0] * len(candidates)

        corpus = [self._tokenize(f"{c['title']} {c['content']}") for c in candidates]
        query_tokens = self._tokenize(query)

        bm25 = BM25Okapi(corpus)
        raw_scores = bm25.get_scores(query_tokens).tolist()

        # Normalize to [0, 0.5] range (cosine is [0, 1])
        max_score = max(raw_scores) if raw_scores else 0.0
        if max_score > 0:
            return [score / max_score * 0.5 for score in raw_scores]
        return raw_scores

    @staticmethod
    def _tokenize(text_val: str) -> list[str]:
        normalized = "".join(c.lower() if c.isalnum() else " " for c in text_val)
        return [token for token in normalized.split() if token]
