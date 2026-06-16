import pytest

from src.core.config import Settings
from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.ports import ChatRequest, ChatResponse
from src.infrastructure.llm.registry import ProviderRegistry


class FakeProvider:
    def complete(self, request: ChatRequest) -> ChatResponse:
        return ChatResponse(content="fake", model=request.model)


def test_registry_returns_cached_provider() -> None:
    registry = ProviderRegistry(
        Settings(llm_provider="openai", llm_model="openai:gpt-4o-mini", openai_api_key="test")
    )
    registry._builders["openai"] = lambda _: FakeProvider()

    provider = registry.get_chat_provider()
    same_provider = registry.get_chat_provider("openai:gpt-4o-mini")

    assert isinstance(provider, FakeProvider)
    assert provider is same_provider


def test_registry_rejects_unknown_model() -> None:
    registry = ProviderRegistry(Settings())

    with pytest.raises(AppError) as exc_info:
        registry.get_chat_provider("openai:not-real")

    assert exc_info.value.code == ErrorCode.LLM_MODEL_NOT_ALLOWED


def test_registry_requires_api_key_for_real_provider() -> None:
    registry = ProviderRegistry(Settings(llm_model="openai:gpt-4o-mini", openai_api_key=None))

    with pytest.raises(AppError) as exc_info:
        registry.get_chat_provider()

    assert exc_info.value.code == ErrorCode.LLM_API_KEY_MISSING
