"""Central model routing helpers for AI features."""

from __future__ import annotations

from dataclasses import dataclass

from scholarlead_agent.config import AppConfig


FEATURE_AGENT_REASONING = "agent_reasoning"
FEATURE_EMAIL_DRAFT = "email_draft"
FEATURE_CUSTOMER_ANALYSIS = "customer_analysis"
FEATURE_SCORE_EXPLANATION = "score_explanation"
FEATURE_REPORT_GENERATION = "report_generation"


@dataclass(frozen=True)
class ModelRuntimeConfig:
    """Resolved non-secret model settings for one feature module."""

    provider: str
    account_alias: str
    base_url: str | None
    model_name: str | None
    fallback_model_name: str | None


def resolve_feature_model_name(
    config: AppConfig,
    feature_module: str | None,
) -> str | None:
    """Resolve the configured model name for one feature."""

    if feature_module == FEATURE_AGENT_REASONING and config.agent_default_model:
        return config.agent_default_model
    if feature_module == FEATURE_EMAIL_DRAFT and config.email_draft_default_model:
        return config.email_draft_default_model
    return config.openai_model


def resolve_model_runtime_config(
    config: AppConfig,
    feature_module: str | None,
) -> ModelRuntimeConfig:
    """Return non-secret model runtime settings for display and logging."""

    return ModelRuntimeConfig(
        provider=config.openai_provider,
        account_alias=config.openai_account_alias,
        base_url=config.openai_base_url,
        model_name=resolve_feature_model_name(config, feature_module),
        fallback_model_name=config.openai_fallback_model,
    )
