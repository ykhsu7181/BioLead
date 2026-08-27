"""OpenAI-compatible Chat Completions adapter for Agent Loop."""

from __future__ import annotations

import time
from typing import Any

import requests

from scholarlead_agent.agent.model import ModelReply, ModelUsage
from scholarlead_agent.ai.model_config import resolve_feature_model_name
from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.pubmed_client import RETRYABLE_STATUS_CODES


class LLMAdapterError(RuntimeError):
    """Base error for LLM adapter failures."""


class LLMConfigError(LLMAdapterError):
    """Raised when model configuration is missing."""


class LLMRequestError(LLMAdapterError):
    """Raised when a provider request fails."""


class OpenAICompatibleChatAdapter:
    """ModelClient implementation for OpenAI-compatible chat APIs."""

    def __init__(
        self,
        *,
        config: AppConfig | None = None,
        session: requests.Session | None = None,
        retry_delay_seconds: float = 1.0,
        feature_module: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.config = config or load_config()
        self.session = session or requests.Session()
        self.retry_delay_seconds = retry_delay_seconds
        self.model_name = model_name or resolve_feature_model_name(
            self.config,
            feature_module,
        )
        self._validate_config()

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        """Call the provider and return a normalized model reply."""

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response_payload = self._post_chat_completions(payload)
        return _normalize_chat_completion_response(response_payload)

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = _build_chat_completions_url(self.config.openai_base_url or "")
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.config.retry_count + 1):
            try:
                response = self.session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.config.request_timeout_seconds,
                )
            except requests.RequestException as error:
                if attempt == self.config.retry_count:
                    raise LLMRequestError(f"model request failed: {error}") from error
                time.sleep(self.retry_delay_seconds)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == self.config.retry_count:
                    raise LLMRequestError(
                        f"model request failed with HTTP {response.status_code}"
                    )
                time.sleep(self.retry_delay_seconds)
                continue

            if response.status_code >= 400:
                raise LLMRequestError(
                    f"model request failed with HTTP {response.status_code}"
                )

            try:
                data = response.json()
            except ValueError as error:
                raise LLMRequestError("model response was not valid JSON") from error
            if not isinstance(data, dict):
                raise LLMRequestError("model response must be a JSON object")
            return data

        raise LLMRequestError("model request failed after retries")

    def _validate_config(self) -> None:
        missing = []
        if not self.config.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if not self.config.openai_base_url:
            missing.append("OPENAI_BASE_URL")
        if not self.model_name:
            missing.append("OPENAI_MODEL")
        if missing:
            raise LLMConfigError(
                "missing model configuration: " + ", ".join(missing)
            )


def _normalize_chat_completion_response(payload: dict[str, Any]) -> ModelReply:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMRequestError("model response missing choices")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise LLMRequestError("model choice must be an object")

    message = first_choice.get("message") or {}
    if not isinstance(message, dict):
        raise LLMRequestError("model message must be an object")

    return ModelReply(
        content=_optional_string(message.get("content")),
        tool_calls=_normalize_tool_calls(message.get("tool_calls")),
        finish_reason=_optional_string(first_choice.get("finish_reason")) or "stop",
        usage=_normalize_usage(payload.get("usage")),
        model=_optional_string(payload.get("model")),
    )


def _normalize_tool_calls(raw_tool_calls: Any) -> list[dict[str, Any]]:
    if raw_tool_calls is None:
        return []
    if not isinstance(raw_tool_calls, list):
        raise LLMRequestError("tool_calls must be a list")

    normalized: list[dict[str, Any]] = []
    for item in raw_tool_calls:
        if not isinstance(item, dict):
            raise LLMRequestError("tool_call must be an object")
        function = item.get("function") or {}
        if not isinstance(function, dict):
            raise LLMRequestError("tool_call.function must be an object")
        normalized.append(
            {
                "id": _optional_string(item.get("id")) or "",
                "type": _optional_string(item.get("type")) or "function",
                "function": {
                    "name": _optional_string(function.get("name")) or "",
                    "arguments": (
                        function.get("arguments")
                        if isinstance(function.get("arguments"), str)
                        else "{}"
                    ),
                },
            }
        )
    return normalized


def _normalize_usage(raw_usage: Any) -> ModelUsage | None:
    if raw_usage is None:
        return None
    if not isinstance(raw_usage, dict):
        return ModelUsage()
    return ModelUsage(
        input_tokens=_optional_int(raw_usage.get("prompt_tokens")),
        output_tokens=_optional_int(raw_usage.get("completion_tokens")),
        total_tokens=_optional_int(raw_usage.get("total_tokens")),
    )


def _build_chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
