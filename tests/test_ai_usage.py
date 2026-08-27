import json
from pathlib import Path
from typing import Any

import pytest

from scholarlead_agent.agent.model import ModelReply, ModelUsage
from scholarlead_agent.ai.model_config import (
    FEATURE_AGENT_REASONING,
    FEATURE_EMAIL_DRAFT,
    resolve_feature_model_name,
)
from scholarlead_agent.ai.usage import (
    AIUsageRecord,
    ModelPrice,
    UsageTrackingModelClient,
    ai_usage_record_to_dict,
    estimate_model_cost,
    load_ai_usage_records,
    save_ai_usage_record,
    summarize_ai_usage,
)
from scholarlead_agent.config import AppConfig


class FakeModel:
    def __init__(
        self,
        *,
        reply: ModelReply | None = None,
        error: Exception | None = None,
    ) -> None:
        self.reply = reply or ModelReply(
            content="ok",
            model="provider-model",
            usage=ModelUsage(input_tokens=10, output_tokens=5, total_tokens=15),
        )
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.calls.append({"messages": messages, "tools": tools})
        if self.error is not None:
            raise self.error
        return self.reply


def make_config(**overrides: Any) -> AppConfig:
    values = {
        "openai_api_key": "sk-test-secret",
        "openai_provider": "openai_compatible",
        "openai_account_alias": "test-account",
        "openai_model": "base-model",
        "agent_default_model": "agent-model",
        "email_draft_default_model": "email-model",
        "ai_pricing_config_version": "test-prices-v1",
    }
    values.update(overrides)
    return AppConfig(**values)


def test_usage_tracking_model_client_saves_success_record(tmp_path: Path) -> None:
    config = make_config(ai_usage_dir=tmp_path)
    wrapped = UsageTrackingModelClient(
        inner=FakeModel(),
        feature_module=FEATURE_AGENT_REASONING,
        config=config,
        task_id="task-1",
    )

    reply = wrapped.complete(messages=[{"role": "user", "content": "hi"}], tools=[])
    records = load_ai_usage_records(tmp_path)

    assert reply.content == "ok"
    assert len(records) == 1
    assert records[0]["feature_module"] == FEATURE_AGENT_REASONING
    assert records[0]["model_name"] == "provider-model"
    assert records[0]["input_tokens"] == 10
    assert records[0]["output_tokens"] == 5
    assert records[0]["total_tokens"] == 15
    assert records[0]["status"] == "success"
    assert records[0]["task_id"] == "task-1"
    assert "sk-test-secret" not in json.dumps(records[0])


def test_usage_tracking_model_client_saves_missing_token_record(tmp_path: Path) -> None:
    wrapped = UsageTrackingModelClient(
        inner=FakeModel(reply=ModelReply(content="ok", model="provider-model")),
        feature_module=FEATURE_EMAIL_DRAFT,
        config=make_config(ai_usage_dir=tmp_path),
        lead_id="lead-1",
    )

    wrapped.complete(messages=[], tools=[])
    record = load_ai_usage_records(tmp_path)[0]

    assert record["feature_module"] == FEATURE_EMAIL_DRAFT
    assert record["input_tokens"] is None
    assert record["output_tokens"] is None
    assert record["total_tokens"] is None
    assert record["estimated_cost"] is None
    assert record["currency"] is None
    assert record["lead_id"] == "lead-1"


def test_usage_tracking_model_client_saves_failure_record(tmp_path: Path) -> None:
    wrapped = UsageTrackingModelClient(
        inner=FakeModel(error=RuntimeError("model down")),
        feature_module=FEATURE_AGENT_REASONING,
        config=make_config(ai_usage_dir=tmp_path),
    )

    with pytest.raises(RuntimeError, match="model down"):
        wrapped.complete(messages=[], tools=[])

    record = load_ai_usage_records(tmp_path)[0]
    assert record["status"] == "failed"
    assert record["error_type"] == "RuntimeError"
    assert record["error_message"] == "model down"
    assert record["model_name"] == "agent-model"


def test_estimate_model_cost_unknown_price_returns_nulls() -> None:
    cost, currency = estimate_model_cost(
        model_name="unknown-model",
        usage=ModelUsage(input_tokens=100, output_tokens=50, total_tokens=150),
    )

    assert cost is None
    assert currency is None


def test_estimate_model_cost_uses_explicit_catalog() -> None:
    cost, currency = estimate_model_cost(
        model_name="priced-model",
        usage=ModelUsage(input_tokens=1000, output_tokens=2000, total_tokens=3000),
        price_catalog={
            "priced-model": ModelPrice(
                input_per_million=1.0,
                output_per_million=2.0,
                currency="USD",
            )
        },
    )

    assert cost == 0.005
    assert currency == "USD"


def test_multiple_usage_records_can_be_summarized(tmp_path: Path) -> None:
    config = make_config()
    save_ai_usage_record(
        AIUsageRecord(
            usage_id="usage-1",
            account_alias="test-account",
            provider="openai_compatible",
            called_at="2026-08-20T10:00:00",
            feature_module=FEATURE_AGENT_REASONING,
            model_name="agent-model",
            input_tokens=3,
            output_tokens=4,
            total_tokens=7,
            estimated_cost=None,
            currency=None,
            pricing_config_version=config.ai_pricing_config_version,
            status="success",
            error_type=None,
            error_message=None,
            task_id=None,
            lead_id=None,
            started_at="2026-08-20T10:00:00",
            finished_at="2026-08-20T10:00:01",
            latency_ms=1000,
        ),
        tmp_path,
    )
    save_ai_usage_record(
        AIUsageRecord(
            usage_id="usage-2",
            account_alias="test-account",
            provider="openai_compatible",
            called_at="2026-08-20T10:01:00",
            feature_module=FEATURE_EMAIL_DRAFT,
            model_name="email-model",
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            currency=None,
            pricing_config_version=config.ai_pricing_config_version,
            status="failed",
            error_type="RuntimeError",
            error_message="failed",
            task_id=None,
            lead_id="lead-1",
            started_at="2026-08-20T10:01:00",
            finished_at="2026-08-20T10:01:01",
            latency_ms=1000,
        ),
        tmp_path,
    )

    records = load_ai_usage_records(tmp_path)
    summary = summarize_ai_usage(records)

    assert len(records) == 2
    assert {record["feature_module"] for record in records} == {
        FEATURE_AGENT_REASONING,
        FEATURE_EMAIL_DRAFT,
    }
    assert summary == {
        "call_count": 2,
        "success_count": 1,
        "failed_count": 1,
        "total_tokens": 7,
        "estimated_cost": None,
    }


def test_ai_usage_record_to_dict_has_stable_fields() -> None:
    data = ai_usage_record_to_dict(
        AIUsageRecord(
            usage_id="usage-1",
            account_alias="alias",
            provider="provider",
            called_at="2026-08-20T10:00:00",
            feature_module=FEATURE_AGENT_REASONING,
            model_name="model",
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            currency=None,
            pricing_config_version="unconfigured",
            status="success",
            error_type=None,
            error_message=None,
            task_id=None,
            lead_id=None,
            started_at="2026-08-20T10:00:00",
            finished_at="2026-08-20T10:00:00",
            latency_ms=0,
        )
    )

    assert list(data) == [
        "usage_id",
        "account_alias",
        "provider",
        "called_at",
        "feature_module",
        "model_name",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost",
        "currency",
        "pricing_config_version",
        "status",
        "error_type",
        "error_message",
        "task_id",
        "lead_id",
        "started_at",
        "finished_at",
        "latency_ms",
    ]


def test_feature_model_resolution_supports_module_defaults() -> None:
    config = make_config()

    assert resolve_feature_model_name(config, FEATURE_AGENT_REASONING) == "agent-model"
    assert resolve_feature_model_name(config, FEATURE_EMAIL_DRAFT) == "email-model"
    assert resolve_feature_model_name(config, "other") == "base-model"
