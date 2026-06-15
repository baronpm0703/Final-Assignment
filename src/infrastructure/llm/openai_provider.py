from typing import Any

import httpx

from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.ports import ChatRequest, ChatResponse, ToolCall


class OpenAIChatProvider:
    def __init__(self, api_key: str, *, base_url: str = "https://api.openai.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def complete(self, request: ChatRequest) -> ChatResponse:
        provider_name, model_name = request.model.split(":", 1)
        if provider_name != "openai":
            raise AppError(
                ErrorCode.LLM_MODEL_NOT_ALLOWED, "OpenAI provider requires openai:* model."
            )

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.tools:
            payload["tools"] = request.tools

        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AppError(ErrorCode.LLM_REQUEST_FAILED, str(exc)) from exc

        data = response.json()
        message = data["choices"][0]["message"]
        tool_calls = [
            ToolCall(
                name=tool_call.get("function", {}).get("name", ""),
                arguments=tool_call.get("function", {}).get("arguments", {}),
            )
            for tool_call in message.get("tool_calls", [])
        ]
        return ChatResponse(
            content=message.get("content") or "",
            model=request.model,
            tool_calls=tool_calls,
            raw=data,
        )
