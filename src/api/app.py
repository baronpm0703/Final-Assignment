from fastapi import FastAPI

from src.agents.data_agent import DataAgent
from src.agents.prompts import load_data_agent_system_prompt
from src.api.routes import router
from src.core.config import Settings, get_settings
from src.core.logging import configure_logging
from src.domain.config import DomainConfig, get_domain_config
from src.infrastructure.database import Database
from src.infrastructure.llm.registry import ProviderRegistry
from src.memory.conversation_memory import ConversationMemory
from src.rag.knowledge_service import KnowledgeService
from src.router.intent_router import IntentRouter


def build_default_agent(settings: Settings, domain_config: DomainConfig) -> DataAgent:
    llm = ProviderRegistry(settings).get_chat_provider(settings.llm_model)
    return DataAgent(
        router=IntentRouter.default(domain_config, llm=llm, llm_model=settings.llm_model),
        knowledge_service=KnowledgeService.from_markdown(domain_config.knowledge.root_path),
        database=Database.from_settings(settings, domain_config),
        llm=llm,
        llm_model=settings.llm_model,
        domain_config=domain_config,
        system_prompt=load_data_agent_system_prompt(domain_config.prompts.system_prompt_path),
    )


def create_app(
    settings: Settings | None = None,
    *,
    agent: DataAgent | None = None,
    memory: ConversationMemory | None = None,
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
    app.include_router(router)
    return app
