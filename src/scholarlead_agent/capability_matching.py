"""Deterministic sender capability matching for academic email drafts."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any

from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.sender_capabilities import (
    SenderCapability,
    SenderCapabilityCatalog,
)


CAPABILITY_MATCHER_VERSION = "rule-v1"
CAPABILITY_MATCH_STATUS_MATCHED = "matched"
CAPABILITY_MATCH_STATUS_PARTIAL = "partial_match"
CAPABILITY_MATCH_STATUS_NO_MATCH = "no_match"
MIN_RELIABLE_MATCH_SCORE = 0.24


@dataclass(frozen=True)
class CapabilityMatchInput:
    """Paper evidence used for deterministic sender capability matching."""

    paper_title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    research_direction: str | None = None
    organism: str | None = None
    lead_id: str | None = None


@dataclass(frozen=True)
class CapabilityMatchItem:
    """One approved capability selected from the catalog."""

    capability_id: str
    capability_name: str
    match_score: float
    match_reason: str
    matched_terms: list[str]
    evidence: list[str]


@dataclass(frozen=True)
class CapabilityMatchResult:
    """A versioned, deterministic set of matched sender capabilities."""

    capability_match_id: str
    lead_id: str | None
    items: list[CapabilityMatchItem]
    status: str
    profile_version: str
    matcher_version: str = CAPABILITY_MATCHER_VERSION


def match_sender_capabilities(
    match_input: CapabilityMatchInput,
    catalog: SenderCapabilityCatalog,
) -> CapabilityMatchResult:
    """Select up to the catalog maximum from approved enabled capabilities.

    The matcher uses only provided paper evidence and catalog configuration. It
    does not call an LLM and does not use company service matching or lead score.
    """

    candidates: list[CapabilityMatchItem] = []
    for capability in catalog.enabled_capabilities:
        item = _score_capability(match_input, capability)
        if item.match_score >= MIN_RELIABLE_MATCH_SCORE:
            candidates.append(item)

    candidates.sort(key=lambda item: (-item.match_score, item.capability_id))
    items = candidates[: catalog.selection_policy.max_candidate_count]
    status = _status_for_count(len(items))

    return CapabilityMatchResult(
        capability_match_id=_build_match_id(match_input, catalog, items),
        lead_id=_clean_text(match_input.lead_id),
        items=items,
        status=status,
        profile_version=catalog.profile_version,
    )


def capability_match_input_from_lead(lead: PubMedLead) -> CapabilityMatchInput:
    """Build matching input from a lead without inferring research direction.

    `target_service_type` is deliberately not reused as `research_direction`.
    It represents an internal service tag rather than paper evidence.
    """

    return CapabilityMatchInput(
        paper_title=lead.recent_publication_title,
        abstract=lead.abstract,
        keywords=list(lead.matched_keywords),
        matched_keywords=list(lead.matched_keywords),
        lead_id=lead.lead_id,
    )


def capability_match_result_to_dict(result: CapabilityMatchResult) -> dict[str, Any]:
    """Convert a result into API- and export-ready plain data."""

    return {
        "capability_match_id": result.capability_match_id,
        "lead_id": result.lead_id,
        "items": [
            {
                "capability_id": item.capability_id,
                "capability_name": item.capability_name,
                "match_score": item.match_score,
                "match_reason": item.match_reason,
                "matched_terms": list(item.matched_terms),
                "evidence": list(item.evidence),
            }
            for item in result.items
        ],
        "status": result.status,
        "profile_version": result.profile_version,
        "matcher_version": result.matcher_version,
    }


def _score_capability(
    match_input: CapabilityMatchInput,
    capability: SenderCapability,
) -> CapabilityMatchItem:
    text = _normalized_input_text(match_input)
    positive_terms = _matched_terms(text, capability.positive_keywords)
    synonym_terms = _matched_terms(text, capability.synonyms)
    research_terms = _matched_terms(text, capability.research_fields)
    question_terms = _matched_terms(text, capability.scientific_questions)
    method_terms = _matched_terms(text, capability.methods)

    score = _score_terms(
        positive_terms=positive_terms,
        synonym_terms=synonym_terms,
        research_terms=research_terms,
        question_terms=question_terms,
        method_terms=method_terms,
    )
    matched_terms = _unique_terms(
        [
            *positive_terms,
            *synonym_terms,
            *research_terms,
            *question_terms,
            *method_terms,
        ]
    )
    evidence = [f"matched term: {term}" for term in matched_terms]

    return CapabilityMatchItem(
        capability_id=capability.capability_id,
        capability_name=capability.capability_name,
        match_score=score,
        match_reason=_match_reason(capability, matched_terms, score),
        matched_terms=matched_terms,
        evidence=evidence,
    )


def _score_terms(
    *,
    positive_terms: list[str],
    synonym_terms: list[str],
    research_terms: list[str],
    question_terms: list[str],
    method_terms: list[str],
) -> float:
    score = (
        min(len(positive_terms) * 0.24, 0.48)
        + min(len(synonym_terms) * 0.16, 0.32)
        + min(len(research_terms) * 0.10, 0.16)
        + min(len(question_terms) * 0.06, 0.10)
        + min(len(method_terms) * 0.10, 0.16)
    )
    return round(min(score, 1.0), 2)


def _status_for_count(item_count: int) -> str:
    if item_count >= 4:
        return CAPABILITY_MATCH_STATUS_MATCHED
    if item_count > 0:
        return CAPABILITY_MATCH_STATUS_PARTIAL
    return CAPABILITY_MATCH_STATUS_NO_MATCH


def _normalized_input_text(match_input: CapabilityMatchInput) -> str:
    parts = [
        match_input.paper_title,
        match_input.abstract,
        " ".join(match_input.keywords),
        " ".join(match_input.matched_keywords),
        match_input.research_direction or "",
        match_input.organism or "",
    ]
    return _normalize_text(" ".join(parts))


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return _unique_terms(
        [term for term in terms if _contains_term(text, _normalize_text(term))]
    )


def _contains_term(text: str, normalized_term: str) -> bool:
    if not normalized_term:
        return False
    if re.search(r"[^a-z0-9 _-]", normalized_term):
        return normalized_term in text
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])", text) is not None


def _unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        cleaned = _clean_text(term)
        normalized = _normalize_text(cleaned or "")
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(cleaned or "")
    return unique


def _match_reason(
    capability: SenderCapability,
    matched_terms: list[str],
    score: float,
) -> str:
    if not matched_terms:
        return f"No catalog terms matched {capability.capability_name}."
    return (
        f"{capability.capability_name} matched catalog terms: "
        f"{', '.join(matched_terms)} (score={score:.2f})."
    )


def _build_match_id(
    match_input: CapabilityMatchInput,
    catalog: SenderCapabilityCatalog,
    items: list[CapabilityMatchItem],
) -> str:
    payload = {
        "lead_id": _clean_text(match_input.lead_id),
        "input": _normalized_input_text(match_input),
        "capability_ids": [item.capability_id for item in items],
        "profile_version": catalog.profile_version,
        "matcher_version": CAPABILITY_MATCHER_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:16]
    return f"capability-match-{digest}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
