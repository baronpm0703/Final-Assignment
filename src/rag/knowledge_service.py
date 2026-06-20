from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from src.rag.embedder import Embedder, HashingEmbedder, cosine_similarity

if TYPE_CHECKING:
    pass

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
    def __init__(self, chunks: list[KnowledgeChunk] | None = None) -> None:
        self.chunks = chunks or []

    def upsert(self, chunks: list[KnowledgeChunk]) -> None:
        self.chunks = chunks

    def search(
        self,
        query_embedding: list[float],
        *,
        limit: int = 5,
        query: str = "",
    ) -> list[RetrievedChunk]:
        query_tokens = self._tokens(query)
        scored = [
            RetrievedChunk(
                source=chunk.source,
                title=chunk.title,
                content=chunk.content,
                score=cosine_similarity(query_embedding, chunk.embedding)
                + self._lexical_score(query_tokens, chunk),
            )
            for chunk in self.chunks
        ]
        return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:limit]

    def _lexical_score(self, query_tokens: set[str], chunk: KnowledgeChunk) -> float:
        if not query_tokens:
            return 0.0
        haystack = f"{chunk.title} {chunk.content}"
        chunk_tokens = self._tokens(haystack)
        overlap = len(query_tokens & chunk_tokens)
        exact_bonus = sum(1 for token in query_tokens if token in haystack.lower())
        return overlap * 0.08 + exact_bonus * 0.02

    def _tokens(self, text: str) -> set[str]:
        normalized = "".join(char.lower() if char.isalnum() else " " for char in text)
        return {token for token in normalized.split() if token}


class KnowledgeService:
    def __init__(self, embedder: Embedder, store: InMemoryKnowledgeStore) -> None:
        self.embedder = embedder
        self.store = store

    @classmethod
    def from_markdown(
        cls,
        root: Path | None = None,
        *,
        embedder: Embedder | None = None,
    ) -> KnowledgeService:
        """Build KnowledgeService from markdown files.

        Args:
            root: Path to knowledge directory. Defaults to "knowledge".
            embedder: Embedder instance. Defaults to HashingEmbedder (offline).
                      Pass OpenAIEmbedder for higher-quality semantic search.
        """
        root = root or Path("knowledge")
        embedder = embedder or HashingEmbedder()
        chunks = MarkdownKnowledgeLoader(root).load(embedder)
        logger.info(
            "KnowledgeService loaded: %d chunks, embedder=%s, dimensions=%d",
            len(chunks),
            type(embedder).__name__,
            embedder.dimensions,
        )
        return cls(embedder=embedder, store=InMemoryKnowledgeStore(chunks))

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        return self.store.search(self.embedder.embed(query), limit=limit, query=query)
