"""Ingest knowledge markdown files into pgvector.

Usage:
    python -m scripts.ingest_kb
    # or: uv run python -m scripts.ingest_kb

Reads all .md files from the knowledge directory, embeds them using
the configured embedder (OpenAI if API key set, else HashingEmbedder),
and upserts into the kb_chunks pgvector table.
"""

from src.core.config import get_settings
from src.domain.config import get_domain_config
from src.infrastructure.database import create_database_engine
from src.infrastructure.vector_store import PgVectorKnowledgeStore
from src.rag.embedder import HashingEmbedder, OpenAIEmbedder
from src.rag.knowledge_service import MarkdownKnowledgeLoader


def main() -> None:
    settings = get_settings()
    domain_config = get_domain_config(str(settings.domain_config_path))

    # Build embedder (OpenAI if key available, else Hashing fallback)
    if settings.openai_api_key:
        print(
            f"Using OpenAIEmbedder (model={settings.embedding_model},"
            f" dims={settings.embedding_dimensions})"
        )
        embedder = OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    else:
        print("No OPENAI_API_KEY set — using HashingEmbedder (lower quality)")
        embedder = HashingEmbedder(dimensions=settings.embedding_dimensions)

    # Load and embed knowledge chunks
    chunks = MarkdownKnowledgeLoader(domain_config.knowledge.root_path).load(embedder)
    print(f"Loaded {len(chunks)} chunks from {domain_config.knowledge.root_path}")

    # Upsert into pgvector
    engine = create_database_engine(str(settings.database_url))
    store = PgVectorKnowledgeStore(engine)
    store.upsert(chunks)
    print(f"Ingested {len(chunks)} knowledge chunks into pgvector (table: kb_chunks)")


if __name__ == "__main__":
    main()
