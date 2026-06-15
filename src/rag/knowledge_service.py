from dataclasses import dataclass
from pathlib import Path

from src.rag.embedder import HashingEmbedder, cosine_similarity


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

    def load(self, embedder: HashingEmbedder) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for path in sorted(self.root.rglob("*.md")):
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                continue
            title = self._title(text, path)
            for content in self._chunk_text(text):
                chunks.append(
                    KnowledgeChunk(
                        source=str(path.relative_to(self.root)),
                        title=title,
                        content=content,
                        embedding=embedder.embed(content),
                    )
                )
        return chunks

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

    def search(self, query_embedding: list[float], *, limit: int = 5) -> list[RetrievedChunk]:
        scored = [
            RetrievedChunk(
                source=chunk.source,
                title=chunk.title,
                content=chunk.content,
                score=cosine_similarity(query_embedding, chunk.embedding),
            )
            for chunk in self.chunks
        ]
        return sorted(scored, key=lambda chunk: chunk.score, reverse=True)[:limit]


class KnowledgeService:
    def __init__(self, embedder: HashingEmbedder, store: InMemoryKnowledgeStore) -> None:
        self.embedder = embedder
        self.store = store

    @classmethod
    def from_markdown(cls, root: Path | None = None) -> "KnowledgeService":
        root = root or Path("knowledge")
        embedder = HashingEmbedder()
        chunks = MarkdownKnowledgeLoader(root).load(embedder)
        return cls(embedder=embedder, store=InMemoryKnowledgeStore(chunks))

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievedChunk]:
        if not query.strip():
            return []
        return self.store.search(self.embedder.embed(query), limit=limit)
