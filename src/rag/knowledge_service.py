from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rank_bm25 import BM25Okapi

from src.rag.embedder import Embedder, HashingEmbedder, cosine_similarity

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from src.infrastructure.vector_store import PgVectorKnowledgeStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KnowledgeChunk:
    source: str
    title: str
    content: str
    embedding: list[float]


@dataclass(frozen=True)
class RetrievedChunk:
    source: str
    title: str
    content: str
    score: float


class MarkdownKnowledgeLoader:
    def __init__(self, root: Path, *, chunk_size: int = 900, overlap: int = 120) -> None:
        self.root = root
        self.chunk_size = chunk_size
        self.overlap = overlap

    def load(self, embedder: Embedder) -> list[KnowledgeChunk]:
        """Load and embed all markdown files. Uses batch embedding when available."""
        raw_chunks: list[tuple[str, str, str]] = []  # (source, title, content)
        for path in sorted(self.root.rglob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            title = self._title(text, path)
            for content in self._chunk_text(text):
                raw_chunks.append((str(path.relative_to(self.root)), title, content))

        if not raw_chunks:
            return []

        # Use batch embedding if available (OpenAIEmbedder) for efficiency
        contents = [content for _, _, content in raw_chunks]
        if hasattr(embedder, "embed_batch"):
            logger.info("Embedding %d chunks via batch API...", len(contents))
            embeddings = embedder.embed_batch(contents)
        else:
            logger.info("Embedding %d chunks one-by-one...", len(contents))
            embeddings = [embedder.embed(content) for content in contents]

        return [
            KnowledgeChunk(
                source=source,
                title=title,
                content=content,
                embedding=embedding,
            )
            for (source, title, content), embedding in zip(raw_chunks, embeddings, strict=True)
        ]

    def _title(self, text: str, path: Path) -> str:
        first_line = text.splitlines()[0].strip()
        if first_line.startswith("#"):
            return first_line.lstrip("#").strip()
        return path.stem.replace("_", " ").title()

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end].strip())
            if end == len(text):
                break
            start = max(0, end - self.overlap)
        return chunks


class InMemoryKnowledgeStore:
    """In-memory vector store with hybrid search (cosine + BM25).

    Uses rank_bm25 for lexical scoring — provides IDF weighting (rare terms
    score higher) and document length normalization, replacing the naive
    token-overlap heuristic.
    """

    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        self.chunks = chunks or []
        self._bm25: BM25Okapi | None = None
        self._bm25_corpus: list[list[str]] = []
        if self.chunks:
            self._build_bm25_index()

    def upsert(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks = chunks
        self._build_bm25_index()

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        query: str = "",
    ) -> list[RetrievedChunk]:
        # Semantic scores (cosine similarity)
        semantic_scores = [
            cosine_similarity(query_embedding, chunk.embedding) for chunk in self.chunks
        ]

        # BM25 lexical scores
        bm25_scores = self._bm25_score(query)

        # Combine: semantic + normalized BM25
        scored = [
            RetrievedChunk(
                source=chunk.source,
                title=chunk.title,
                content=chunk.content,
                score=semantic + bm25,
            )
            for chunk, semantic, bm25 in zip(
                self.chunks, semantic_scores, bm25_scores, strict=True
            )
        ]
        return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:limit]

    def _build_bm25_index(self) -> None:
        """Build BM25 index from chunk titles + content."""
        self._bm25_corpus = [
            self._tokenize(f"{chunk.title} {chunk.content}") for chunk in self.chunks
        ]
        self._bm25 = BM25Okapi(self._bm25_corpus)

    def _bm25_score(self, query: str) -> list[float]:
        """Get BM25 scores for all chunks, normalized to [0, ~0.5] range."""
        if not self._bm25 or not query.strip():
            return [0.0] * len(self.chunks)

        query_tokens = self._tokenize(query)
        raw_scores = self._bm25.get_scores(query_tokens).tolist()

        # Normalize BM25 scores to comparable range with cosine similarity.
        # Cosine sim is in [-1, 1], typically [0.3, 0.9] for relevant chunks.
        # BM25 raw scores can be 0-20+. Scale so max BM25 contributes ~0.5.
        max_score = max(raw_scores) if raw_scores else 0.0
        if max_score > 0:
            return [score / max_score * 0.5 for score in raw_scores]
        return raw_scores

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace tokenizer with normalization."""
        normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
        return [token for token in normalized.split() if token]


class KnowledgeService:
    """Unified knowledge retrieval service.

    Supports two backends:
      - InMemoryKnowledgeStore (default, for tests / small KBs)
      - PgVectorKnowledgeStore (production, persistent, ANN search)
    """

    def __init__(
        self,
        embedder: Embedder,
        store: InMemoryKnowledgeStore | None = None,
        *,
        pgvector_store: PgVectorKnowledgeStore | None = None,
    ) -> None:
        self.embedder = embedder
        self._memory_store = store
        self._pgvector_store = pgvector_store

    @property
    def _use_pgvector(self) -> bool:
        return self._pgvector_store is not None

    @classmethod
    def from_markdown(
        cls,
        root: Path | None = None,
        *,
        embedder: Embedder | None = None,
    ) -> KnowledgeService:
        """Build KnowledgeService with in-memory store from markdown files.

        Suitable for tests and local development without a database.
        """
        root = root or Path("knowledge")
        embedder = embedder or HashingEmbedder()
        chunks = MarkdownKnowledgeLoader(root).load(embedder)
        logger.info(
            "KnowledgeService (in-memory): %d chunks, embedder=%s, dimensions=%d",
            len(chunks),
            type(embedder).__name__,
            embedder.dimensions,
        )
        return cls(embedder=embedder, store=InMemoryKnowledgeStore(chunks))

    @classmethod
    def from_pgvector(
        cls,
        engine: Engine,
        *,
        embedder: Embedder | None = None,
        table_name: str = "kb_chunks",
        dimensions: int = 1536,
        knowledge_root: Path | None = None,
    ) -> KnowledgeService:
        """Build KnowledgeService backed by pgvector.

        On first run (table empty), loads markdown files from knowledge_root,
        embeds them, and inserts into the pgvector table.
        Subsequent runs skip ingestion if the table already has data.
        """
        from src.infrastructure.vector_store import PgVectorKnowledgeStore

        embedder = embedder or HashingEmbedder()
        pg_store = PgVectorKnowledgeStore(
            engine=engine, table_name=table_name, dimensions=dimensions
        )
        pg_store.init_table()

        # Auto-ingest knowledge if table is empty
        if pg_store.count() == 0:
            knowledge_root = knowledge_root or Path("knowledge")
            logger.info("pgvector table empty — ingesting knowledge from %s", knowledge_root)
            chunks = MarkdownKnowledgeLoader(knowledge_root).load(embedder)
            if chunks:
                pg_store.upsert([
                    {
                        "source": c.source,
                        "title": c.title,
                        "content": c.content,
                        "embedding": c.embedding,
                    }
                    for c in chunks
                ])
            logger.info("Ingested %d chunks into pgvector", len(chunks))
        else:
            logger.info(
                "KnowledgeService (pgvector): %d chunks in table '%s'",
                pg_store.count(),
                table_name,
            )

        return cls(embedder=embedder, pgvector_store=pg_store)

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievedChunk]:
        if not query.strip():
            return []

        query_embedding = self.embedder.embed(query)

        if self._use_pgvector:
            results = self._pgvector_store.search(  # type: ignore[union-attr]
                query_embedding, limit=limit, query=query
            )
            return [
                RetrievedChunk(
                    source=r["source"],
                    title=r["title"],
                    content=r["content"],
                    score=r["score"],
                )
                for r in results
            ]

        # Fallback: in-memory store
        if self._memory_store is not None:
            return self._memory_store.search(query_embedding, limit=limit, query=query)

        return []

    def reingest(self, knowledge_root: Path | None = None) -> int:
        """Force re-ingest knowledge into pgvector (truncate + re-embed + insert).

        Returns the number of chunks ingested.
        """
        if not self._use_pgvector:
            raise RuntimeError("reingest() is only supported with pgvector backend")

        knowledge_root = knowledge_root or Path("knowledge")
        chunks = MarkdownKnowledgeLoader(knowledge_root).load(self.embedder)
        if chunks:
            self._pgvector_store.upsert([  # type: ignore[union-attr]
                {
                    "source": c.source,
                    "title": c.title,
                    "content": c.content,
                    "embedding": c.embedding,
                }
                for c in chunks
            ])
        logger.info("Re-ingested %d chunks into pgvector", len(chunks))
        return len(chunks)
