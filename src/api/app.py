from fastapi import FastAPI

from src.agents.data_agent import DataAgent
from src.api.routes import router
from src.core.config import Settings, get_settings
from src.core.logging import configure_logging
from src.infrastructure.database import Database
from src.memory.conversation_memory import ConversationMemory
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter


def build_default_agent(settings: Settings) -> DataAgent:
    return DataAgent(
        router=IntentRouter.default(),
        knowledge_service=KnowledgeService.from_markdown(),
        database=Database.from_settings(settings),
    )


def create_app(
    settings: Settings | None = None,
    *,
    agent: DataAgent | None = None,
    memory: ConversationMemory | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.agent = agent or build_default_agent(settings)
    app.state.memory = memory or ConversationMemory(
        window_size=settings.memory_window_size,
        compaction_ratio=settings.memory_compaction_ratio,
        summary_ratio=settings.memory_summary_ratio,
    )
    app.include_router(router)
    return app
