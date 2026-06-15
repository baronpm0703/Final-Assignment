from pathlib import Path

from src.rag.knowledge_service import KnowledgeService


def test_retrieval_returns_relevant_metric_chunk() -> None:
    service = KnowledgeService.from_markdown(Path("knowledge"))

    chunks = service.retrieve("cong thuc abandon sys theo thang", limit=3)

    assert chunks
    assert any("Abandon_SYS" in chunk.content for chunk in chunks)


def test_empty_query_returns_no_chunks() -> None:
    service = KnowledgeService.from_markdown(Path("knowledge"))

    assert service.retrieve("  ") == []
