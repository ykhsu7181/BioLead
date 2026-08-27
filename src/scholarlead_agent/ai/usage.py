"""AI usage audit records for model calls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from scholarlead_agent.agent.model import ModelClient, ModelReply, ModelUsage
from scholarlead_agent.ai.model_config import resolve_feature_model_name
from scholarlead_agent.config import AppConfig, load_config


@dataclass(frozen=True)
class AIUsageRecord:
    """One model-call usage record without prompts or secrets."""

    usage_id: str
    account_alias: str
    provider: str
    called_at: str
    feature_module: str
    model_name: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    currency: str | None
    pricing_config_version: str
    status: str
    error_type: str | None
    error_message: str | None
    task_id: str | None
    lead_id: str | None
    started_at: str
    finished_at: str
    latency_ms: int


@dataclass(frozen=True)
class ModelPrice:
    """Optional model price configuration per one million tokens."""

    input_per_million: float
    output_per_million: float
    currency: str = "USD"


MODEL_PRICE_CATALOG: dict[str, ModelPrice] = {}


class UsageTrackingModelClient:
    """Wrap a ModelClient and persist one usage record per model call."""

    def __init__(
        self,
        *,
        inner: ModelClient,
        feature_module: str,
        config: AppConfig | None = None,
        usage_dir: Path | str | None = None,
        task_id: str | None = None,
        lead_id: str | None = None,
    ) -> None:
        self.inner = inner
        self.feature_module = feature_module
        self.config = config or load_config()
        self.usage_dir = Path(usage_dir) if usage_dir is not None else self.config.ai_usage_dir
        self.task_id = task_id
        self.lead_id = lead_id

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        """Call the wrapped model and save a success or failure usage record."""

        started_at = _now_iso()
        monotonic_started = time.perf_counter()
        try:
            reply = self.inner.complete(messages=messages, tools=tools)
        except Exception as error:
            finished_at = _now_iso()
            save_ai_usage_record(
                build_ai_usage_record(
                    config=self.config,
                    feature_module=self.feature_module,
                    model_name=resolve_feature_model_name(
                        self.config,
                        self.feature_module,
                    ),
                    usage=None,
                    status="failed",
                    error=error,
                    task_id=self.task_id,
                    lead_id=self.lead_id,
                    started_at=started_at,
                    finished_at=finished_at,
                    latency_ms=_latency_ms(monotonic_started),
                ),
                self.usage_dir,
            )
            raise

        finished_at = _now_iso()
        save_ai_usage_record(
            build_ai_usage_record(
                config=self.config,
                feature_module=self.feature_module,
                model_name=reply.model
                or resolve_feature_model_name(self.config, self.feature_module),
                usage=reply.usage,
                status="success",
                error=None,
                task_id=self.task_id,
                lead_id=self.lead_id,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=_latency_ms(monotonic_started),
            ),
            self.usage_dir,
        )
        return reply


def build_ai_usage_record(
    *,
    config: AppConfig,
    feature_module: str,
    model_name: str | None,
    usage: ModelUsage | None,
    status: str,
    error: Exception | None,
    task_id: str | None,
    lead_id: str | None,
    started_at: str,
    finished_at: str,
    latency_ms: int,
) -> AIUsageRecord:
    """Build one AI usage record from normalized model output."""

    estimated_cost, currency = estimate_model_cost(
        model_name=model_name,
        usage=usage,
    )
    return AIUsageRecord(
        usage_id=str(uuid4()),
        account_alias=config.openai_account_alias,
        provider=config.openai_provider,
        called_at=started_at,
        feature_module=feature_module,
        model_name=model_name,
        input_tokens=usage.input_tokens if usage else None,
        output_tokens=usage.output_tokens if usage else None,
        total_tokens=usage.total_tokens if usage else None,
        estimated_cost=estimated_cost,
        currency=currency,
        pricing_config_version=config.ai_pricing_config_version,
        status=status,
        error_type=error.__class__.__name__ if error else None,
        error_message=str(error) if error else None,
        task_id=task_id,
        lead_id=lead_id,
        started_at=started_at,
        finished_at=finished_at,
        latency_ms=latency_ms,
    )


def estimate_model_cost(
    *,
    model_name: str | None,
    usage: ModelUsage | None,
    price_catalog: dict[str, ModelPrice] | None = None,
) -> tuple[float | None, str | None]:
    """Estimate model cost only when an explicit price is configured."""

    if not model_name or usage is None:
        return None, None

    catalog = price_catalog if price_catalog is not None else MODEL_PRICE_CATALOG
    price = catalog.get(model_name)
    if price is None or usage.input_tokens is None or usage.output_tokens is None:
        return None, None

    estimated = (
        usage.input_tokens * price.input_per_million
        + usage.output_tokens * price.output_per_million
    ) / 1_000_000
    return round(estimated, 8), price.currency


def save_ai_usage_record(record: AIUsageRecord, usage_dir: Path | str) -> Path:
    """Append one usage record as JSONL and return the file path."""

    path = build_ai_usage_log_path(usage_dir, record.called_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(ai_usage_record_to_dict(record), ensure_ascii=False))
        file.write("\n")
    return path


def build_ai_usage_log_path(usage_dir: Path | str, called_at: str) -> Path:
    """Build a daily JSONL usage log path."""

    date_part = called_at[:10].replace("-", "") if called_at else "unknown"
    return Path(usage_dir) / f"ai_usage_{date_part}.jsonl"


def load_ai_usage_records(usage_dir: Path | str, *, limit: int | None = None) -> list[dict[str, Any]]:
    """Load usage records from JSONL files, newest files first."""

    root = Path(usage_dir)
    if not root.exists():
        return []

    records: list[dict[str, Any]] = []
    for path in sorted(root.glob("ai_usage_*.jsonl"), reverse=True):
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
        if limit is not None and len(records) >= limit:
            return records[:limit]
    return records


def summarize_ai_usage(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return a small aggregate summary for UI display."""

    total_tokens = sum(
        value
        for record in records
        for value in [_optional_int(record.get("total_tokens"))]
        if value is not None
    )
    known_cost = [
        value
        for record in records
        for value in [_optional_float(record.get("estimated_cost"))]
        if value is not None
    ]
    return {
        "call_count": len(records),
        "success_count": sum(1 for record in records if record.get("status") == "success"),
        "failed_count": sum(1 for record in records if record.get("status") == "failed"),
        "total_tokens": total_tokens,
        "estimated_cost": round(sum(known_cost), 8) if known_cost else None,
    }


def ai_usage_record_to_dict(record: AIUsageRecord) -> dict[str, Any]:
    """Convert an AI usage record to a stable JSON dictionary."""

    return {
        "usage_id": record.usage_id,
        "account_alias": record.account_alias,
        "provider": record.provider,
        "called_at": record.called_at,
        "feature_module": record.feature_module,
        "model_name": record.model_name,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "total_tokens": record.total_tokens,
        "estimated_cost": record.estimated_cost,
        "currency": record.currency,
        "pricing_config_version": record.pricing_config_version,
        "status": record.status,
        "error_type": record.error_type,
        "error_message": record.error_message,
        "task_id": record.task_id,
        "lead_id": record.lead_id,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "latency_ms": record.latency_ms,
    }


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _latency_ms(started: float) -> int:
    return max(0, round((time.perf_counter() - started) * 1000))


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
