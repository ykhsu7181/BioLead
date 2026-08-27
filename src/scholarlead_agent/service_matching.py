"""Deterministic company service matching."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.service_catalog import CompanyService, CompanyServiceCatalog


SERVICE_MATCHER_VERSION = "rule-v1"


@dataclass(frozen=True)
class ServiceMatchInput:
    """Input text used by ServiceMatcher."""

    paper_title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)
    research_direction: str | None = None
    organism: str | None = None


@dataclass(frozen=True)
class ServiceMatchResult:
    """One service matching result."""

    service_id: str | None
    service_name: str | None
    match_score: float
    match_reason: str
    matched_terms: list[str]
    evidence: list[str]
    status: str
    catalog_version: str
    matcher_version: str = SERVICE_MATCHER_VERSION


def match_company_service(
    match_input: ServiceMatchInput,
    catalog: CompanyServiceCatalog,
) -> ServiceMatchResult:
    """Return the best matching enabled company service."""

    best: ServiceMatchResult | None = None
    disabled_match_seen = False
    for service in catalog.services:
        result = _score_service(match_input, service, catalog.catalog_version)
        if result.status == "disabled_service":
            if result.match_score > 0:
                disabled_match_seen = True
            continue
        if best is None or result.match_score > best.match_score:
            best = result

    if best is not None and best.match_score > 0:
        return best

    return ServiceMatchResult(
        service_id=None,
        service_name=None,
        match_score=0.0,
        match_reason="No enabled company service matched the input evidence.",
        matched_terms=[],
        evidence=[],
        status="disabled_service" if disabled_match_seen else "no_match",
        catalog_version=catalog.catalog_version,
    )


def service_match_input_from_lead(lead: PubMedLead) -> ServiceMatchInput:
    """Build a ServiceMatchInput from an existing PubMed Lead."""

    return ServiceMatchInput(
        paper_title=lead.recent_publication_title,
        abstract=lead.abstract,
        keywords=lead.matched_keywords,
        matched_keywords=lead.matched_keywords,
        research_direction=lead.target_service_type,
    )


def service_match_result_to_dict(result: ServiceMatchResult) -> dict[str, Any]:
    """Convert a service match result to a JSON-friendly dict."""

    return {
        "service_id": result.service_id,
        "service_name": result.service_name,
        "match_score": result.match_score,
        "match_reason": result.match_reason,
        "matched_terms": list(result.matched_terms),
        "evidence": list(result.evidence),
        "status": result.status,
        "catalog_version": result.catalog_version,
        "matcher_version": result.matcher_version,
    }


def _score_service(
    match_input: ServiceMatchInput,
    service: CompanyService,
    catalog_version: str,
) -> ServiceMatchResult:
    text = _normalized_input_text(match_input)
    positive_terms = _matched_terms(text, service.positive_keywords)
    synonym_terms = _matched_terms(text, service.synonyms)
    application_terms = _matched_terms(text, service.application_fields)
    organism_terms = _matched_terms(text, service.supported_organisms)
    negative_terms = _matched_terms(text, service.negative_keywords)

    score = (
        len(positive_terms) * 0.28
        + len(synonym_terms) * 0.22
        + len(application_terms) * 0.18
        + len(organism_terms) * 0.08
        - len(negative_terms) * 0.35
    )
    score = max(0.0, min(1.0, round(score, 2)))

    matched_terms = _unique_terms(
        [*positive_terms, *synonym_terms, *application_terms, *organism_terms]
    )
    evidence = [
        f"matched term: {term}"
        for term in matched_terms
    ]
    if negative_terms:
        evidence.extend(f"negative term: {term}" for term in negative_terms)

    if not service.enabled:
        status = "disabled_service"
    elif score >= 0.3:
        status = "matched"
    elif score > 0:
        status = "needs_review"
    else:
        status = "no_match"

    return ServiceMatchResult(
        service_id=service.service_id if service.enabled else None,
        service_name=service.service_name if service.enabled else None,
        match_score=score,
        match_reason=_match_reason(status, service, matched_terms, negative_terms),
        matched_terms=matched_terms,
        evidence=evidence,
        status=status,
        catalog_version=catalog_version,
    )


def _normalized_input_text(match_input: ServiceMatchInput) -> str:
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
    matched: list[str] = []
    for term in terms:
        normalized = _normalize_text(term)
        if normalized and _contains_term(text, normalized):
            matched.append(term)
    return _unique_terms(matched)


def _contains_term(text: str, term: str) -> bool:
    if " " in term or "-" in term:
        return term in text
    return re.search(rf"\b{re.escape(term)}\b", text) is not None


def _unique_terms(terms: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = _normalize_text(term)
        if key and key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def _match_reason(
    status: str,
    service: CompanyService,
    matched_terms: list[str],
    negative_terms: list[str],
) -> str:
    if status == "disabled_service":
        return f"{service.service_name} matched but is disabled in the catalog."
    if status == "no_match":
        return f"No terms matched {service.service_name}."
    if negative_terms:
        return (
            f"{service.service_name} has positive evidence but also negative terms: "
            f"{', '.join(negative_terms)}."
        )
    return f"{service.service_name} matched terms: {', '.join(matched_terms)}."


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().strip())

