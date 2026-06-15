import pytest

from src.core.config import Settings
from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.ports import ChatMessage, ChatRequest
from src.infrastructure.llm.registry import MockChatProvider, ProviderRegistry


def test_registry_returns_cached_mock_provider() -> None:
    registry = ProviderRegistry(Settings(llm_model="mock:offline"))

    provider = registry.get_chat_provider()
    same_provider = registry.get_chat_provider("mock:offline")

    assert isinstance(provider, MockChatProvider)
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


def test_mock_provider_returns_offline_response() -> None:
    provider = MockChatProvider()

    response = provider.complete(
        ChatRequest(
            model="mock:offline",
            messages=[ChatMessage(role="user", content="hello")],
        )
    )

    assert response.model == "mock:offline"
    assert "hello" in response.content
