from typing import Any

import httpx

from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.ports import ChatRequest, ChatResponse


class GeminiChatProvider:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def complete(self, request: ChatRequest) -> ChatResponse:
        provider_name, model_name = request.model.split(":", 1)
        if provider_name != "gemini":
            raise AppError(
                ErrorCode.LLM_MODEL_NOT_ALLOWED, "Gemini provider requires gemini:* model."
            )

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
                for message in request.messages
                if message.role != "system"
            ],
            "generationConfig": {"temperature": request.temperature},
        }
        system_instruction = "\n".join(
            message.content for message in request.messages if message.role == "system"
        )
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            response = httpx.post(
                f"{self.base_url}/models/{model_name}:generateContent",
                params={"key": self.api_key},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(ErrorCode.LLM_REQUEST_FAILED, str(exc)) from exc

        data = response.json()
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        content = "\n".join(part.get("text", "") for part in parts)
        return ChatResponse(content=content, model=request.model, raw=data)
