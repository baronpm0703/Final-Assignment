import logging

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from src.agents.data_agent import DataAgent
from src.agents.prompts import load_data_agent_system_prompt
from src.api.routes import router
from src.core.config import Settings, get_settings
from src.core.logging import configure_logging
from src.domain.config import DomainConfig, get_domain_config
from src.infrastructure.database import Database, create_database_engine
from src.infrastructure.llm.registry import ProviderRegistry
from src.memory.conversation_memory import ConversationMemory
from src.memory.conversation_store import ConversationStore
from src.rag.embedder import Embedder, HashingEmbedder, OpenAIEmbedder
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter

logger = logging.getLogger(__name__)


def _build_embedder(settings: Settings) -> Embedder:
    """Build the appropriate embedder based on settings.

    Uses OpenAIEmbedder when an API key is available, falls back to HashingEmbedder.
    """
    if settings.openai_api_key:
        logger.info(
            "Using OpenAIEmbedder (model=%s, dimensions=%d)",
            settings.embedding_model,
            settings.embedding_dimensions,
        )
        return OpenAIEmbedder(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )
    logger.info("No OpenAI API key found, falling back to HashingEmbedder")
    return HashingEmbedder()


def _build_knowledge_service(
    settings: Settings, domain_config: DomainConfig, embedder: Embedder
) -> KnowledgeService:
    """Build knowledge service — pgvector if DB available, else in-memory fallback."""
    try:
        from src.infrastructure.database import create_database_engine
        from src.infrastructure.vector_store import PgVectorKnowledgeStore

        engine = create_database_engine(str(settings.database_url))
        store = PgVectorKnowledgeStore(engine)

        # Check if pgvector table has data
        if store.count() > 0:
            logger.info("Using PgVectorKnowledgeStore (%d chunks in DB)", store.count())
            return KnowledgeService.from_pgvector(
                engine=engine,
                embedder=embedder,
                knowledge_root=domain_config.knowledge.root_path,
                dimensions=settings.embedding_dimensions,
            )
        else:
            logger.info("pgvector table empty — auto-ingesting knowledge")
            return KnowledgeService.from_pgvector(
                engine=engine,
                embedder=embedder,
                knowledge_root=domain_config.knowledge.root_path,
                dimensions=settings.embedding_dimensions,
            )
    except Exception as exc:
        logger.warning("Failed to connect to pgvector, falling back to in-memory store: %s", exc)
        return KnowledgeService.from_markdown(domain_config.knowledge.root_path, embedder=embedder)


def build_default_agent(settings: Settings, domain_config: DomainConfig) -> DataAgent:
    llm = ProviderRegistry(settings).get_chat_provider(settings.llm_model)
    embedder = _build_embedder(settings)
    return DataAgent(
        router=IntentRouter.default(domain_config, llm=llm, llm_model=settings.llm_model),
        knowledge_service=_build_knowledge_service(settings, domain_config, embedder),
        database=Database.from_settings(settings, domain_config),
        llm=llm,
        llm_model=settings.llm_model,
        domain_config=domain_config,
        system_prompt=load_data_agent_system_prompt(domain_config.prompts.system_prompt_path),
    )


def build_conversation_store(settings: Settings) -> ConversationStore | None:
    try:
        store = ConversationStore(create_database_engine(str(settings.database_url)))
        store.ensure_schema()
    except SQLAlchemyError as exc:
        logger.warning(
            "Conversation persistence is unavailable, falling back to in-memory only: %s",
            exc,
        )
        return None
    return store


def create_app(
    settings: Settings | None = None,
    *,
    agent: DataAgent | None = None,
    memory: ConversationMemory | None = None,
    conversation_store: ConversationStore | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    domain_config = get_domain_config(str(settings.domain_config_path))

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.domain_config = domain_config
    app.state.agent = agent or build_default_agent(settings, domain_config)
    app.state.memory = memory or ConversationMemory(
        window_size=settings.memory_window_size,
        compaction_ratio=settings.memory_compaction_ratio,
        summary_ratio=settings.memory_summary_ratio,
    )
    app.state.conversation_store = (
        conversation_store if conversation_store is not None else build_conversation_store(settings)
    )
    app.include_router(router)
    return app
