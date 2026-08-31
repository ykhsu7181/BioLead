"""Sender capability catalog loading and validation for email drafting."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_SENDER_CAPABILITIES_PATH = Path("data/config/sender_capabilities.json")
ZERO_MATCH_STRATEGY_PAPER_ONLY = "paper_only"


@dataclass(frozen=True)
class SenderCapabilitySelectionPolicy:
    """Selection limits and safety rules for a capability catalog."""

    target_candidate_count: int
    max_candidate_count: int
    min_candidate_count: int
    allow_fewer_when_evidence_is_insufficient: bool
    zero_match_strategy: str
    llm_may_create_new_capabilities: bool
    note: str | None = None


@dataclass(frozen=True)
class SenderCapability:
    """One approved sender capability available for future matching."""

    capability_id: str
    capability_name: str
    category: str
    description: str
    positive_keywords: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    research_fields: list[str] = field(default_factory=list)
    scientific_questions: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    enabled: bool = True


@dataclass(frozen=True)
class SenderCapabilityCatalog:
    """Versioned catalog of approved sender capabilities."""

    profile_version: str
    purpose: str
    selection_policy: SenderCapabilitySelectionPolicy
    capabilities: list[SenderCapability]
    source_policy: dict[str, Any]
    source_path: str

    @property
    def enabled_capabilities(self) -> list[SenderCapability]:
        """Return approved capabilities enabled for future matching."""

        return [capability for capability in self.capabilities if capability.enabled]


def load_sender_capability_catalog(
    path: Path | str | None = None,
) -> SenderCapabilityCatalog:
    """Load and validate a versioned sender capability catalog.

    This function does not perform capability matching or invoke an LLM.
    """

    source_path = Path(
        path or os.getenv("SENDER_CAPABILITIES_PATH") or DEFAULT_SENDER_CAPABILITIES_PATH
    )
    if not source_path.exists():
        raise FileNotFoundError(f"sender capability catalog not found: {source_path}")

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"sender capability catalog is not valid JSON: {source_path}") from error
    if not isinstance(payload, dict):
        raise ValueError("sender capability catalog must be a JSON object")

    capabilities_payload = payload.get("capabilities")
    if not isinstance(capabilities_payload, list) or not capabilities_payload:
        raise ValueError("capabilities must be a non-empty list")

    capabilities = [_capability_from_payload(item) for item in capabilities_payload]
    _validate_unique_capability_ids(capabilities)

    return SenderCapabilityCatalog(
        profile_version=_required_text(payload, "profile_version"),
        purpose=_required_text(payload, "purpose"),
        selection_policy=_selection_policy_from_payload(payload.get("selection_policy")),
        capabilities=capabilities,
        source_policy=_source_policy_from_payload(payload.get("source_policy")),
        source_path=str(source_path),
    )


def sender_capability_catalog_to_dict(
    catalog: SenderCapabilityCatalog,
) -> dict[str, Any]:
    """Return catalog metadata and capability records without hidden state."""

    return {
        "profile_version": catalog.profile_version,
        "purpose": catalog.purpose,
        "selection_policy": {
            "target_candidate_count": catalog.selection_policy.target_candidate_count,
            "max_candidate_count": catalog.selection_policy.max_candidate_count,
            "min_candidate_count": catalog.selection_policy.min_candidate_count,
            "allow_fewer_when_evidence_is_insufficient": (
                catalog.selection_policy.allow_fewer_when_evidence_is_insufficient
            ),
            "zero_match_strategy": catalog.selection_policy.zero_match_strategy,
            "llm_may_create_new_capabilities": (
                catalog.selection_policy.llm_may_create_new_capabilities
            ),
            "note": catalog.selection_policy.note,
        },
        "capabilities": [
            {
                "capability_id": capability.capability_id,
                "capability_name": capability.capability_name,
                "category": capability.category,
                "description": capability.description,
                "positive_keywords": list(capability.positive_keywords),
                "synonyms": list(capability.synonyms),
                "research_fields": list(capability.research_fields),
                "scientific_questions": list(capability.scientific_questions),
                "methods": list(capability.methods),
                "enabled": capability.enabled,
            }
            for capability in catalog.capabilities
        ],
        "source_policy": dict(catalog.source_policy),
        "source_path": catalog.source_path,
    }


def _capability_from_payload(value: Any) -> SenderCapability:
    if not isinstance(value, dict):
        raise ValueError("each capability must be a JSON object")
    enabled = value.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("enabled must be a boolean in sender capability catalog")

    return SenderCapability(
        capability_id=_required_text(value, "capability_id"),
        capability_name=_required_text(value, "capability_name"),
        category=_required_text(value, "category"),
        description=_required_text(value, "description"),
        positive_keywords=_required_text_list(value, "positive_keywords"),
        synonyms=_required_text_list(value, "synonyms"),
        research_fields=_required_text_list(value, "research_fields"),
        scientific_questions=_required_text_list(value, "scientific_questions"),
        methods=_required_text_list(value, "methods"),
        enabled=enabled,
    )


def _selection_policy_from_payload(value: Any) -> SenderCapabilitySelectionPolicy:
    if not isinstance(value, dict):
        raise ValueError("selection_policy must be a JSON object")

    target = _required_non_negative_int(value, "target_candidate_count")
    maximum = _required_non_negative_int(value, "max_candidate_count")
    minimum = _required_non_negative_int(value, "min_candidate_count")
    if minimum > target or target > maximum:
        raise ValueError("selection policy counts must satisfy min <= target <= max")

    allow_fewer = value.get("allow_fewer_when_evidence_is_insufficient")
    if not isinstance(allow_fewer, bool):
        raise ValueError("allow_fewer_when_evidence_is_insufficient must be a boolean")

    zero_match_strategy = _required_text(value, "zero_match_strategy")
    if zero_match_strategy != ZERO_MATCH_STRATEGY_PAPER_ONLY:
        raise ValueError("zero_match_strategy must be paper_only")

    llm_may_create = value.get("llm_may_create_new_capabilities")
    if llm_may_create is not False:
        raise ValueError("llm_may_create_new_capabilities must be false")

    return SenderCapabilitySelectionPolicy(
        target_candidate_count=target,
        max_candidate_count=maximum,
        min_candidate_count=minimum,
        allow_fewer_when_evidence_is_insufficient=allow_fewer,
        zero_match_strategy=zero_match_strategy,
        llm_may_create_new_capabilities=llm_may_create,
        note=_optional_text(value.get("note")),
    )


def _source_policy_from_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("source_policy must be a JSON object")
    return dict(value)


def _validate_unique_capability_ids(capabilities: list[SenderCapability]) -> None:
    seen: set[str] = set()
    for capability in capabilities:
        if capability.capability_id in seen:
            raise ValueError(
                f"duplicate capability_id in sender capability catalog: "
                f"{capability.capability_id}"
            )
        seen.add(capability.capability_id)


def _required_non_negative_int(payload: dict[str, Any], field_name: str) -> int:
    value = payload.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _required_text(payload: dict[str, Any], field_name: str) -> str:
    value = _optional_text(payload.get(field_name))
    if not value:
        raise ValueError(f"{field_name} is required in sender capability catalog")
    return value


def _required_text_list(payload: dict[str, Any], field_name: str) -> list[str]:
    value = payload.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list in sender capability catalog")
    cleaned = [_optional_text(item) for item in value]
    result = [item for item in cleaned if item]
    if not result or len(result) != len(value):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return result


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
