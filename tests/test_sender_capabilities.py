import json
from pathlib import Path

import pytest

from scholarlead_agent.sender_capabilities import (
    ZERO_MATCH_STRATEGY_PAPER_ONLY,
    load_sender_capability_catalog,
    sender_capability_catalog_to_dict,
)


def make_catalog_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "profile_version": "2026-08-28-v1",
        "purpose": "Approved capability catalog for email drafting.",
        "selection_policy": {
            "target_candidate_count": 4,
            "max_candidate_count": 6,
            "min_candidate_count": 0,
            "allow_fewer_when_evidence_is_insufficient": True,
            "zero_match_strategy": "paper_only",
            "llm_may_create_new_capabilities": False,
        },
        "capabilities": [
            {
                "capability_id": "single_cell_rna_seq",
                "capability_name": "Single-cell RNA sequencing",
                "category": "Single-cell genomics",
                "description": "Single-cell transcriptomic profiling.",
                "positive_keywords": ["single-cell RNA-seq"],
                "synonyms": ["scRNA-seq"],
                "research_fields": ["cell heterogeneity"],
                "scientific_questions": ["Which cell states are present?"],
                "methods": ["10x Genomics"],
                "enabled": True,
            }
        ],
        "source_policy": {"intended_use": "internal capability matching"},
    }
    payload.update(overrides)
    return payload


def write_catalog(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "sender_capabilities.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_load_sender_capability_catalog_from_json(tmp_path: Path) -> None:
    path = write_catalog(tmp_path, make_catalog_payload())

    catalog = load_sender_capability_catalog(path)

    assert catalog.profile_version == "2026-08-28-v1"
    assert catalog.selection_policy.target_candidate_count == 4
    assert catalog.selection_policy.max_candidate_count == 6
    assert catalog.selection_policy.zero_match_strategy == ZERO_MATCH_STRATEGY_PAPER_ONLY
    assert catalog.selection_policy.llm_may_create_new_capabilities is False
    assert catalog.capabilities[0].capability_id == "single_cell_rna_seq"
    assert catalog.enabled_capabilities == catalog.capabilities
    assert catalog.source_path == str(path)


def test_catalog_to_dict_is_configuration_safe(tmp_path: Path) -> None:
    catalog = load_sender_capability_catalog(write_catalog(tmp_path, make_catalog_payload()))

    data = sender_capability_catalog_to_dict(catalog)

    assert data["selection_policy"]["zero_match_strategy"] == "paper_only"
    assert data["capabilities"][0]["methods"] == ["10x Genomics"]
    assert "password" not in json.dumps(data).lower()


def test_load_sender_capability_catalog_rejects_missing_required_field(tmp_path: Path) -> None:
    payload = make_catalog_payload()
    capability = dict(payload["capabilities"][0])
    capability.pop("capability_name")
    payload["capabilities"] = [capability]

    with pytest.raises(ValueError, match="capability_name is required"):
        load_sender_capability_catalog(write_catalog(tmp_path, payload))


def test_load_sender_capability_catalog_rejects_duplicate_ids(tmp_path: Path) -> None:
    payload = make_catalog_payload()
    capability = dict(payload["capabilities"][0])
    payload["capabilities"] = [payload["capabilities"][0], capability]

    with pytest.raises(ValueError, match="duplicate capability_id"):
        load_sender_capability_catalog(write_catalog(tmp_path, payload))


def test_load_sender_capability_catalog_rejects_invalid_selection_policy(tmp_path: Path) -> None:
    payload = make_catalog_payload()
    policy = dict(payload["selection_policy"])
    policy["target_candidate_count"] = "4-6"
    payload["selection_policy"] = policy

    with pytest.raises(ValueError, match="target_candidate_count must be a non-negative integer"):
        load_sender_capability_catalog(write_catalog(tmp_path, payload))


def test_disabled_capability_is_loaded_but_not_enabled_for_matching(tmp_path: Path) -> None:
    payload = make_catalog_payload()
    capability = dict(payload["capabilities"][0])
    capability["capability_id"] = "disabled_capability"
    capability["enabled"] = False
    payload["capabilities"] = [payload["capabilities"][0], capability]

    catalog = load_sender_capability_catalog(write_catalog(tmp_path, payload))

    assert len(catalog.capabilities) == 2
    assert [item.capability_id for item in catalog.enabled_capabilities] == [
        "single_cell_rna_seq"
    ]


def test_load_project_sender_capability_catalog() -> None:
    catalog = load_sender_capability_catalog()

    assert catalog.profile_version == "2026-08-28-sender-capabilities-v1"
    assert len(catalog.capabilities) == 39
    assert len(catalog.enabled_capabilities) == 39
    assert catalog.selection_policy.target_candidate_count == 4
    assert catalog.selection_policy.max_candidate_count == 6
    assert catalog.selection_policy.min_candidate_count == 0
