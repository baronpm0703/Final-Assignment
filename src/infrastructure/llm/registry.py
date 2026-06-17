from collections.abc import Callable

from src.core.config import Settings
from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.gemini_provider import GeminiChatProvider
from src.infrastructure.llm.openai_provider import OpenAIChatProvider
from src.infrastructure.llm.ports import ChatCompletionPort

ALLOWED_MODELS: dict[str, set[str]] = {
    "openai": {"gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"},
    "gemini": {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"},
}


ProviderBuilder = Callable[[Settings], ChatCompletionPort]


class ProviderRegistry:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._providers: dict[str, ChatCompletionPort] = {}
        self._builders: dict[str, ProviderBuilder] = {
            "openai": self._build_openai,
            "gemini": self._build_gemini,
        }

    def get_chat_provider(self, model_id: str | None = None) -> ChatCompletionPort:
        provider_name, model_name = self.parse_model_id(model_id or self.settings.llm_model)
        self._validate_model(provider_name, model_name)

        if provider_name not in self._builders:
            raise AppError(
                ErrorCode.LLM_PROVIDER_UNSUPPORTED,
                f"Unsupported LLM provider '{provider_name}'.",
            )

        if provider_name not in self._providers:
            self._providers[provider_name] = self._builders[provider_name](self.settings)
        return self._providers[provider_name]

    @staticmethod
    def parse_model_id(model_id: str) -> tuple[str, str]:
        if ":" not in model_id:
            raise AppError(
                ErrorCode.LLM_MODEL_NOT_ALLOWED,
                "Model id must use '<provider>:<model>' format.",
            )
        provider_name, model_name = model_id.split(":", 1)
        return provider_name.strip().lower(), model_name.strip()

    def _validate_model(self, provider_name: str, model_name: str) -> None:
        allowed_models = ALLOWED_MODELS.get(provider_name)
        if allowed_models is None or model_name not in allowed_models:
            raise AppError(
                ErrorCode.LLM_MODEL_NOT_ALLOWED,
                f"Model '{provider_name}:{model_name}' is not allowed.",
            )

    def _build_openai(self, settings: Settings) -> ChatCompletionPort:
        if not settings.openai_api_key:
            raise AppError(ErrorCode.LLM_API_KEY_MISSING, "OPENAI_API_KEY is required.")
        return OpenAIChatProvider(api_key=settings.openai_api_key)

    def _build_gemini(self, settings: Settings) -> ChatCompletionPort:
        if not settings.gemini_api_key:
            raise AppError(ErrorCode.LLM_API_KEY_MISSING, "GEMINI_API_KEY is required.")
        return GeminiChatProvider(api_key=settings.gemini_api_key)
