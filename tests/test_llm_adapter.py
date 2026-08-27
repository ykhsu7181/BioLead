from typing import Any

import pytest
import requests

from scholarlead_agent.adapters.openai_compatible_chat import (
    LLMConfigError,
    LLMRequestError,
    OpenAICompatibleChatAdapter,
)
from scholarlead_agent.ai.model_config import FEATURE_EMAIL_DRAFT
from scholarlead_agent.config import AppConfig, load_config


class FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self.payload


class FakeSession:
    def __init__(
        self,
        responses: list[FakeResponse] | None = None,
        error: requests.RequestException | None = None,
    ) -> None:
        self.responses = responses or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if self.error is not None:
            raise self.error
        return self.responses.pop(0)


def make_config(**overrides: Any) -> AppConfig:
    values = {
        "openai_api_key": "sk-test-secret",
        "openai_base_url": "https://llm.example.test/v1",
        "openai_model": "test-chat-model",
        "retry_count": 0,
    }
    values.update(overrides)
    return AppConfig(**values)


def test_load_config_reads_openai_compatible_environment(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_PROVIDER", "test-provider")
    monkeypatch.setenv("OPENAI_ACCOUNT_ALIAS", "research-account")
    monkeypatch.setenv("CROSSREF_BASE_URL", "https://crossref.example.test")
    monkeypatch.setenv("CROSSREF_USER_AGENT", "ScholarLeadAgent test")
    monkeypatch.setenv("CROSSREF_MAILTO", "contact@example.test")
    monkeypatch.setenv("OPENAI_API_KEY", "local-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("OPENAI_MODEL", "model-a")
    monkeypatch.setenv("OPENAI_FALLBACK_MODEL", "model-b")
    monkeypatch.setenv("AGENT_DEFAULT_MODEL", "agent-model")
    monkeypatch.setenv("EMAIL_DRAFT_DEFAULT_MODEL", "email-model")
    monkeypatch.setenv("AI_USAGE_DIR", "data/processed/test_ai_usage")
    monkeypatch.setenv("EMAIL_AUDIT_DIR", "data/processed/test_email_audit")
    monkeypatch.setenv("DATABASE_PATH", "data/processed/test.sqlite")
    monkeypatch.setenv("TOKEN_WARNING_THRESHOLD", "1000")
    monkeypatch.setenv("COST_WARNING_THRESHOLD", "2.5")
    monkeypatch.setenv("AI_PRICING_CONFIG_VERSION", "local-prices")

    config = load_config()

    assert config.openai_provider == "test-provider"
    assert config.openai_account_alias == "research-account"
    assert config.crossref_base_url == "https://crossref.example.test"
    assert config.crossref_user_agent == "ScholarLeadAgent test"
    assert config.crossref_mailto == "contact@example.test"
    assert config.openai_api_key == "local-key"
    assert config.openai_base_url == "https://example.test/v1"
    assert config.openai_model == "model-a"
    assert config.openai_fallback_model == "model-b"
    assert config.agent_default_model == "agent-model"
    assert config.email_draft_default_model == "email-model"
    assert config.ai_usage_dir.parts == ("data", "processed", "test_ai_usage")
    assert config.email_audit_dir.parts == ("data", "processed", "test_email_audit")
    assert config.database_path.parts == ("data", "processed", "test.sqlite")
    assert config.token_warning_threshold == 1000
    assert config.cost_warning_threshold == 2.5
    assert config.ai_pricing_config_version == "local-prices"


def test_adapter_normalizes_text_reply_and_usage() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "model": "provider-model",
                    "choices": [
                        {
                            "message": {"content": "Hello"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 11,
                        "completion_tokens": 7,
                        "total_tokens": 18,
                    },
                },
            )
        ]
    )
    adapter = OpenAICompatibleChatAdapter(
        config=make_config(),
        session=session,
        retry_delay_seconds=0,
    )

    reply = adapter.complete(messages=[{"role": "user", "content": "hi"}], tools=[])

    assert reply.content == "Hello"
    assert reply.tool_calls == []
    assert reply.finish_reason == "stop"
    assert reply.model == "provider-model"
    assert reply.usage is not None
    assert reply.usage.input_tokens == 11
    assert reply.usage.output_tokens == 7
    assert reply.usage.total_tokens == 18
    assert session.calls[0]["url"] == "https://llm.example.test/v1/chat/completions"
    assert session.calls[0]["json"]["model"] == "test-chat-model"
    assert "tools" not in session.calls[0]["json"]


def test_adapter_uses_feature_default_model() -> None:
    session = FakeSession(
        [FakeResponse(200, {"choices": [{"message": {"content": "Hello"}}]})]
    )
    adapter = OpenAICompatibleChatAdapter(
        config=make_config(email_draft_default_model="email-model"),
        session=session,
        feature_module=FEATURE_EMAIL_DRAFT,
    )

    adapter.complete(messages=[], tools=[])

    assert session.calls[0]["json"]["model"] == "email-model"


def test_adapter_normalizes_single_tool_call_and_preserves_arguments_string() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "model": "provider-model",
                    "choices": [
                        {
                            "message": {
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "search_pubmed",
                                            "arguments": "{\"query\":\"crispr\"}",
                                        },
                                    }
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                },
            )
        ]
    )
    adapter = OpenAICompatibleChatAdapter(config=make_config(), session=session)

    reply = adapter.complete(
        messages=[{"role": "user", "content": "find papers"}],
        tools=[{"type": "function", "function": {"name": "search_pubmed"}}],
    )

    assert reply.finish_reason == "tool_calls"
    assert reply.tool_calls == [
        {
            "id": "call-1",
            "type": "function",
            "function": {
                "name": "search_pubmed",
                "arguments": "{\"query\":\"crispr\"}",
            },
        }
    ]
    assert session.calls[0]["json"]["tool_choice"] == "auto"


def test_adapter_normalizes_multiple_tool_calls() -> None:
    session = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call-a",
                                        "function": {"name": "first", "arguments": "{}"},
                                    },
                                    {
                                        "id": "call-b",
                                        "function": {"name": "second", "arguments": "{}"},
                                    },
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
            )
        ]
    )
    adapter = OpenAICompatibleChatAdapter(config=make_config(), session=session)

    reply = adapter.complete(messages=[], tools=[{"type": "function"}])

    assert [call["id"] for call in reply.tool_calls] == ["call-a", "call-b"]
    assert [call["function"]["name"] for call in reply.tool_calls] == [
        "first",
        "second",
    ]


def test_adapter_handles_missing_optional_fields_as_unknown() -> None:
    session = FakeSession([FakeResponse(200, {"choices": [{"message": {}}]})])
    adapter = OpenAICompatibleChatAdapter(config=make_config(), session=session)

    reply = adapter.complete(messages=[], tools=[])

    assert reply.content is None
    assert reply.tool_calls == []
    assert reply.finish_reason == "stop"
    assert reply.usage is None
    assert reply.model is None


def test_adapter_raises_for_api_error_without_leaking_api_key() -> None:
    session = FakeSession([FakeResponse(401, {"error": {"message": "bad key"}})])
    adapter = OpenAICompatibleChatAdapter(config=make_config(), session=session)

    with pytest.raises(LLMRequestError) as error:
        adapter.complete(messages=[], tools=[])

    assert "HTTP 401" in str(error.value)
    assert "sk-test-secret" not in str(error.value)


def test_adapter_raises_for_network_error() -> None:
    session = FakeSession(error=requests.Timeout("timeout with secret?"))
    adapter = OpenAICompatibleChatAdapter(config=make_config(), session=session)

    with pytest.raises(LLMRequestError, match="model request failed"):
        adapter.complete(messages=[], tools=[])


def test_adapter_requires_model_configuration_without_leaking_key() -> None:
    with pytest.raises(LLMConfigError) as error:
        OpenAICompatibleChatAdapter(
            config=make_config(openai_api_key=None, openai_model=None)
        )

    message = str(error.value)
    assert "OPENAI_API_KEY" in message
    assert "OPENAI_MODEL" in message
    assert "sk-test-secret" not in message


def test_adapter_retries_retryable_http_status() -> None:
    session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]}),
        ]
    )
    adapter = OpenAICompatibleChatAdapter(
        config=make_config(retry_count=1),
        session=session,
        retry_delay_seconds=0,
    )

    reply = adapter.complete(messages=[], tools=[])

    assert reply.content == "ok"
    assert len(session.calls) == 2
