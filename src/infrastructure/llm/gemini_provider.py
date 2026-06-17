import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from src.core.errors import AppError, ErrorCode
from src.infrastructure.llm.ports import ChatRequest, ChatResponse, ToolCall

logger = logging.getLogger(__name__)

_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_DELAY = 2  # seconds
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "llm")


class GeminiChatProvider:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_delay: float = _DEFAULT_BASE_DELAY,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.base_delay = base_delay
        self._call_counter = 0

    def complete(self, request: ChatRequest) -> ChatResponse:
        provider_name, model_name = request.model.split(":", 1)
        if provider_name != "gemini":
            raise AppError(
                ErrorCode.LLM_MODEL_NOT_ALLOWED, "Gemini provider requires gemini:* model."
            )

        payload: dict[str, Any] = {
            "contents": self._build_contents(request),
            "generationConfig": {"temperature": request.temperature},
        }

        # Add system instruction
        system_instruction = "\n".join(
            message.content for message in request.messages if message.role == "system"
        )
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        # Add tools in Gemini's functionDeclarations format
        if request.tools:
            payload["tools"] = self._convert_tools(request.tools)

        # File-based logging: request
        self._call_counter += 1
        self._log_to_file("request", model_name, payload)

        logger.debug(
            "llm_provider_request",
            extra={"provider": "gemini", "model": request.model, "payload": payload},
        )

        url = f"{self.base_url}/models/{model_name}:generateContent"
        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = httpx.post(
                    url,
                    params={"key": self.api_key},
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status in (429, 503) and attempt < self.max_retries:
                    delay = self.base_delay * (2**attempt)
                    logger.warning(
                        "gemini_rate_limited_retrying",
                        extra={
                            "provider": "gemini",
                            "model": request.model,
                            "status": status,
                            "attempt": attempt + 1,
                            "retry_delay": delay,
                        },
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    "llm_provider_request_failed",
                    extra={"provider": "gemini", "model": request.model, "error": str(exc)},
                )
                raise AppError(ErrorCode.LLM_REQUEST_FAILED, str(exc)) from exc
            except httpx.HTTPError as exc:
                last_exc = exc
                logger.warning(
                    "llm_provider_request_failed",
                    extra={"provider": "gemini", "model": request.model, "error": str(exc)},
                )
                raise AppError(ErrorCode.LLM_REQUEST_FAILED, str(exc)) from exc
        else:
            raise AppError(ErrorCode.LLM_REQUEST_FAILED, str(last_exc)) from last_exc

        data = response.json()

        # File-based logging: response
        self._log_to_file("response", model_name, data)

        logger.debug(
            "llm_provider_response",
            extra={"provider": "gemini", "model": request.model, "response": data},
        )

        # Parse response: extract text content AND function calls
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(
                    ToolCall(
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )

        content = "\n".join(text_parts)
        return ChatResponse(
            content=content, model=request.model, tool_calls=tool_calls, raw=data
        )

    def _build_contents(self, request: ChatRequest) -> list[dict[str, Any]]:
        """Build Gemini contents array from ChatMessages, skipping system messages."""
        contents: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "system":
                continue
            role = "model" if message.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message.content}]})
        return contents

    def _convert_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert OpenAI-style tool definitions to Gemini functionDeclarations format.

        OpenAI format:
          [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]

        Gemini format:
          [{"functionDeclarations": [{"name": ..., "description": ..., "parameters": ...}]}]
        """
        declarations: list[dict[str, Any]] = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                decl: dict[str, Any] = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                }
                params = func.get("parameters")
                if params:
                    decl["parameters"] = self._normalize_parameters(params)
                declarations.append(decl)
        if declarations:
            return [{"functionDeclarations": declarations}]
        return []

    def _normalize_parameters(self, params: dict[str, Any]) -> dict[str, Any]:
        """Normalize JSON Schema parameters for Gemini (uppercase type values)."""
        normalized: dict[str, Any] = {}
        for key, value in params.items():
            if key == "type" and isinstance(value, str):
                normalized[key] = value.upper()
            elif key == "properties" and isinstance(value, dict):
                normalized[key] = {
                    prop_name: self._normalize_parameters(prop_schema)
                    for prop_name, prop_schema in value.items()
                }
            else:
                normalized[key] = value
        return normalized

    def _log_to_file(self, direction: str, model_name: str, data: dict[str, Any]) -> None:
        """Write request/response JSON to logs/llm/ for debugging."""
        try:
            log_dir = os.path.abspath(_LOG_DIR)
            os.makedirs(log_dir, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{self._call_counter:04d}_{direction}.json"
            filepath = os.path.join(log_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(
                    {"model": model_name, "direction": direction, "data": data},
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
        except Exception:
            logger.debug("Failed to write LLM log file", exc_info=True)
