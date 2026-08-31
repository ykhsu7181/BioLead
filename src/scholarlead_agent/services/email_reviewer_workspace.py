"""Read-model helpers for the human email draft reviewer workspace."""

from __future__ import annotations

from typing import Any


ABSTRACT_PREVIEW_LIMIT = 600


def build_email_reviewer_workspace(draft: dict[str, Any]) -> dict[str, Any]:
    """Project persisted draft evidence into reviewer-facing, auditable sections.

    This function is read-only: it does not approve, edit, regenerate, or send a
    draft. The original draft payload remains available separately for audit.
    """

    evidence = draft.get("evidence") if isinstance(draft.get("evidence"), dict) else {}
    capability_match = (
        evidence.get("capability_match")
        if isinstance(evidence.get("capability_match"), dict)
        else {}
    )
    quality_report = (
        draft.get("quality_report")
        if isinstance(draft.get("quality_report"), dict)
        else evidence.get("quality_report")
        if isinstance(evidence.get("quality_report"), dict)
        else {}
    )
    matched_service = (
        evidence.get("matched_service")
        if isinstance(evidence.get("matched_service"), dict)
        else {}
    )

    return {
        "review_status": draft.get("draft_status") or "unknown",
        "can_send": bool(draft.get("can_send")),
        "paper_evidence": {
            "title": evidence.get("recent_publication_title") or draft.get("source_paper_title"),
            "abstract_preview": _preview(evidence.get("abstract")),
            "keywords": list(evidence.get("matched_keywords") or []),
            "pmid": evidence.get("pmid") or draft.get("source_pmid"),
            "doi": evidence.get("doi") or draft.get("doi"),
            "source_url": evidence.get("pubmed_source_url") or draft.get("source_url"),
            "source_refs": list(evidence.get("paper_evidence_source_refs") or []),
        },
        "capability_match": {
            "status": capability_match.get("status"),
            "match_id": capability_match.get("capability_match_id"),
            "items": list(capability_match.get("candidate_capabilities") or []),
        },
        "quality_report": quality_report,
        "versions": {
            "draft_mode": evidence.get("draft_mode"),
            "draft_version": draft.get("draft_version") or "v1",
            "prompt_version": evidence.get("email_prompt_version"),
            "sender_profile_version": (evidence.get("sender_profile") or {}).get("profile_version"),
            "capability_profile_version": capability_match.get("profile_version"),
            "capability_matcher_version": capability_match.get("matcher_version"),
            "service_catalog_version": matched_service.get("catalog_version"),
            "service_matcher_version": matched_service.get("matcher_version"),
        },
        "warnings": list(draft.get("warnings") or []),
    }


def _preview(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) <= ABSTRACT_PREVIEW_LIMIT:
        return text
    return f"{text[:ABSTRACT_PREVIEW_LIMIT].rstrip()}..."
