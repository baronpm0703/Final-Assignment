from src.core.config import get_settings
from src.domain.config import get_domain_config
from src.infrastructure.database import create_database_engine
from src.infrastructure.vector_store import PgVectorKnowledgeStore
from src.rag.embedder import HashingEmbedder
from src.rag.knowledge_service import MarkdownKnowledgeLoader


def main() -> None:
    settings = get_settings()
    domain_config = get_domain_config(str(settings.domain_config_path))
    embedder = HashingEmbedder(dimensions=1536)
    chunks = MarkdownKnowledgeLoader(domain_config.knowledge.root_path).load(embedder)
    engine = create_database_engine(str(settings.database_url))
    PgVectorKnowledgeStore(engine).upsert(chunks)
    print(f"Ingested {len(chunks)} knowledge chunks")


if __name__ == "__main__":
    main()
