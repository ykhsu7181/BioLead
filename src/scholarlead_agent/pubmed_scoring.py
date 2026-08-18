"""Deterministic PubMed keyword matching and temporary scoring helpers.

These helpers cover stage 11 keyword matching and stage 12 PubMed-only
temporary scoring. Official multi-source/four-dimension scoring is intentionally
not implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import re

from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper


DEFAULT_KEYWORD_RULE_NOTE = "default rule / pending client keyword hierarchy"
FUNDING_ACTIVITY_REASON = "Funding source not connected in PubMed-only first round"
OFFICIAL_SCORING_STATUS = "pending_multi_source_data"

TOPIC_MATCH_WEIGHT = 0.5
PUBLICATION_RECENCY_WEIGHT = 0.3
EMAIL_CONTACTABILITY_WEIGHT = 0.2

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class PubMedKeywordMatch:
    """Result of deterministic PubMed topic keyword matching."""

    matched_keywords: list[str]
    target_service_type: str | None
    topic_match_score: int
    topic_match_reason: str


@dataclass(frozen=True)
class PubMedTemporaryScore:
    """PubMed-only temporary lead score result."""

    topic_match_score: int
    publication_recency_score: int
    email_contactability_score: int
    lead_score: int
    priority: str
    score_explanation: str
    funding_activity_score: int | None
    funding_activity_reason: str
    outsourcing_tendency_score: int | None
    official_scoring_status: str


def normalize_keywords(keywords: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize keyword text into lowercase, deduplicated terms."""

    if keywords is None:
        return []

    if isinstance(keywords, str):
        raw_values = re.split(r"[,;/|+\n]", keywords)
    else:
        raw_values = list(keywords)

    normalized_values: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        if not isinstance(value, str):
            continue
        normalized = _normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_values.append(normalized)

    return normalized_values


def extract_query_terms(query: str | None) -> list[str]:
    """Extract phrase-first query terms from a user query."""

    phrases = normalize_keywords(query)
    terms: list[str] = []

    for phrase in phrases:
        _append_unique(terms, phrase)

    for phrase in phrases:
        for token in re.findall(r"[a-z0-9][a-z0-9-]*", phrase):
            if len(token) < 3 or token in STOP_WORDS:
                continue
            _append_unique(terms, token)

    return terms


def find_matched_keywords(
    *,
    query: str | None,
    title: str | None = None,
    abstract: str | None = None,
    mesh_terms: list[str] | None = None,
    keywords: list[str] | None = None,
) -> list[str]:
    """Find query terms that appear in title, abstract, MeSH terms, or keywords."""

    query_terms = extract_query_terms(query)
    if not query_terms:
        return []

    searchable_text = _build_searchable_text(
        title=title,
        abstract=abstract,
        mesh_terms=mesh_terms,
        keywords=keywords,
    )
    if not searchable_text:
        return []

    matched: list[str] = []
    matched_phrases: list[str] = []

    for term in query_terms:
        if " " not in term:
            continue
        if _contains_term(searchable_text, term):
            _append_unique(matched, term)
            matched_phrases.append(term)

    for term in query_terms:
        if " " in term or _is_token_covered_by_phrase(term, matched_phrases):
            continue
        if _contains_term(searchable_text, term):
            _append_unique(matched, term)

    return matched


def calculate_topic_match_score(
    matched_keywords: list[str],
    *,
    query_terms: list[str] | None = None,
) -> int:
    """Calculate a deterministic topic match score for stage 11."""

    normalized_matches = normalize_keywords(matched_keywords)
    if not normalized_matches:
        return 0

    normalized_query_terms = normalize_keywords(query_terms)
    if normalized_query_terms and set(normalized_query_terms).issubset(normalized_matches):
        return 100

    if len(normalized_matches) >= 3:
        return 100
    if len(normalized_matches) == 2:
        return 80
    return 60


def build_topic_match_reason(
    *,
    matched_keywords: list[str],
    target_service_type: str | None = None,
) -> str:
    """Build a readable, deterministic topic match reason."""

    normalized_service_type = _normalize_optional_label(target_service_type)
    if not matched_keywords:
        if normalized_service_type:
            return (
                "No matched keywords. "
                f"Target service type: {normalized_service_type}. "
                f"{DEFAULT_KEYWORD_RULE_NOTE}."
            )
        return f"No matched keywords. {DEFAULT_KEYWORD_RULE_NOTE}."

    joined_keywords = ", ".join(matched_keywords)
    if normalized_service_type:
        return (
            f"Matched keywords: {joined_keywords}. "
            f"Target service type: {normalized_service_type}. "
            f"{DEFAULT_KEYWORD_RULE_NOTE}."
        )
    return f"Matched keywords: {joined_keywords}. {DEFAULT_KEYWORD_RULE_NOTE}."


def match_pubmed_keywords(
    *,
    query: str | None,
    title: str | None = None,
    abstract: str | None = None,
    mesh_terms: list[str] | None = None,
    keywords: list[str] | None = None,
    service_type: str | None = None,
) -> PubMedKeywordMatch:
    """Match query terms against PubMed paper fields and tag service type."""

    matched_keywords = find_matched_keywords(
        query=query,
        title=title,
        abstract=abstract,
        mesh_terms=mesh_terms,
        keywords=keywords,
    )
    score = calculate_topic_match_score(
        matched_keywords,
        query_terms=extract_query_terms(query),
    )
    target_service_type = _normalize_optional_label(service_type)

    return PubMedKeywordMatch(
        matched_keywords=matched_keywords,
        target_service_type=target_service_type,
        topic_match_score=score,
        topic_match_reason=build_topic_match_reason(
            matched_keywords=matched_keywords,
            target_service_type=target_service_type,
        ),
    )


def match_pubmed_paper_keywords(
    paper: PubMedPaper,
    *,
    query: str | None,
    service_type: str | None = None,
) -> PubMedKeywordMatch:
    """Match query terms against one parsed PubMed paper."""

    return match_pubmed_keywords(
        query=query,
        title=paper.title,
        abstract=paper.abstract,
        mesh_terms=paper.mesh_terms,
        keywords=paper.keywords,
        service_type=service_type,
    )


def enrich_lead_keyword_match(
    lead: PubMedLead,
    *,
    query: str | None,
    mesh_terms: list[str] | None = None,
    keywords: list[str] | None = None,
    service_type: str | None = None,
) -> PubMedLead:
    """Return a lead with deterministic keyword match fields filled."""

    keyword_match = match_pubmed_keywords(
        query=query,
        title=lead.recent_publication_title,
        abstract=lead.abstract,
        mesh_terms=mesh_terms,
        keywords=keywords,
        service_type=service_type,
    )
    return replace(
        lead,
        matched_keywords=keyword_match.matched_keywords,
        target_service_type=keyword_match.target_service_type,
        topic_match_score=keyword_match.topic_match_score,
        topic_match_reason=keyword_match.topic_match_reason,
    )


def enrich_leads_keyword_match(
    leads: list[PubMedLead],
    *,
    query: str | None,
    service_type: str | None = None,
    paper_by_pmid: dict[str, PubMedPaper] | None = None,
) -> list[PubMedLead]:
    """Return leads with keyword match fields filled."""

    enriched: list[PubMedLead] = []
    for lead in leads:
        paper = paper_by_pmid.get(lead.pmid) if paper_by_pmid else None
        enriched.append(
            enrich_lead_keyword_match(
                lead,
                query=query,
                mesh_terms=paper.mesh_terms if paper is not None else None,
                keywords=paper.keywords if paper is not None else None,
                service_type=service_type,
            )
        )
    return enriched


def score_publication_recency(
    publication_year: int | None,
    *,
    reference_year: int | None = None,
) -> int:
    """Score publication recency for PubMed-only temporary scoring."""

    if publication_year is None:
        return 0

    comparison_year = reference_year if reference_year is not None else date.today().year
    age = comparison_year - publication_year

    if age < 0:
        return 100
    if age <= 2:
        return 100
    if age <= 5:
        return 70
    if age <= 10:
        return 40
    return 0


def score_email_contactability(
    *,
    email_status: str,
    verified_email: str | None,
) -> int:
    """Score email contactability from PubMed email evidence only."""

    if not verified_email:
        return 0

    normalized_status = email_status.strip().lower()
    if normalized_status == "verified_from_pubmed_affiliation":
        return 100
    if normalized_status == "needs_review":
        return 60
    return 0


def assign_priority(lead_score: int) -> str:
    """Assign temporary PubMed-only priority from the lead score."""

    if lead_score >= 80:
        return "high"
    if lead_score >= 50:
        return "medium"
    return "low"


def build_score_explanation(
    *,
    topic_match_score: int,
    publication_recency_score: int,
    email_contactability_score: int,
    lead_score: int,
    priority: str,
) -> str:
    """Build a deterministic explanation for PubMed-only temporary scoring."""

    return (
        "PubMed-only temporary score: "
        f"topic_match_score={topic_match_score} weighted 50%, "
        f"publication_recency_score={publication_recency_score} weighted 30%, "
        f"email_contactability_score={email_contactability_score} weighted 20%, "
        f"lead_score={lead_score}, priority={priority}. "
        "Funding and outsourcing dimensions are not scored because multi-source "
        "data is not connected."
    )


def calculate_pubmed_lead_score(
    *,
    topic_match_score: int,
    publication_recency_score: int,
    email_contactability_score: int,
) -> int:
    """Calculate weighted PubMed-only temporary lead score."""

    weighted_score = (
        _clamp_score(topic_match_score) * TOPIC_MATCH_WEIGHT
        + _clamp_score(publication_recency_score) * PUBLICATION_RECENCY_WEIGHT
        + _clamp_score(email_contactability_score) * EMAIL_CONTACTABILITY_WEIGHT
    )
    return round(weighted_score)


def build_pubmed_temporary_score(
    lead: PubMedLead,
    *,
    reference_year: int | None = None,
) -> PubMedTemporaryScore:
    """Build a deterministic PubMed-only temporary score result."""

    topic_score = _clamp_score(lead.topic_match_score)
    recency_score = score_publication_recency(
        lead.publication_year,
        reference_year=reference_year,
    )
    contactability_score = score_email_contactability(
        email_status=lead.email_status,
        verified_email=lead.verified_email,
    )
    lead_score = calculate_pubmed_lead_score(
        topic_match_score=topic_score,
        publication_recency_score=recency_score,
        email_contactability_score=contactability_score,
    )
    priority = assign_priority(lead_score)

    return PubMedTemporaryScore(
        topic_match_score=topic_score,
        publication_recency_score=recency_score,
        email_contactability_score=contactability_score,
        lead_score=lead_score,
        priority=priority,
        score_explanation=build_score_explanation(
            topic_match_score=topic_score,
            publication_recency_score=recency_score,
            email_contactability_score=contactability_score,
            lead_score=lead_score,
            priority=priority,
        ),
        funding_activity_score=None,
        funding_activity_reason=FUNDING_ACTIVITY_REASON,
        outsourcing_tendency_score=None,
        official_scoring_status=OFFICIAL_SCORING_STATUS,
    )


def score_pubmed_lead(
    lead: PubMedLead,
    *,
    reference_year: int | None = None,
) -> PubMedLead:
    """Return a lead with PubMed-only temporary scoring fields filled."""

    score = build_pubmed_temporary_score(lead, reference_year=reference_year)
    return replace(
        lead,
        topic_match_score=score.topic_match_score,
        publication_recency_score=score.publication_recency_score,
        email_contactability_score=score.email_contactability_score,
        lead_score=score.lead_score,
        priority=score.priority,
        score_explanation=score.score_explanation,
        funding_activity_score=score.funding_activity_score,
        funding_activity_reason=score.funding_activity_reason,
        outsourcing_tendency_score=score.outsourcing_tendency_score,
        official_scoring_status=score.official_scoring_status,
    )


def score_pubmed_leads(
    leads: list[PubMedLead],
    *,
    reference_year: int | None = None,
) -> list[PubMedLead]:
    """Return leads with PubMed-only temporary scoring fields filled."""

    return [score_pubmed_lead(lead, reference_year=reference_year) for lead in leads]


def _build_searchable_text(
    *,
    title: str | None,
    abstract: str | None,
    mesh_terms: list[str] | None,
    keywords: list[str] | None,
) -> str:
    text_parts = [
        title or "",
        abstract or "",
        " ".join(mesh_terms or []),
        " ".join(keywords or []),
    ]
    return _normalize_text(" ".join(text_parts))


def _contains_term(searchable_text: str, term: str) -> bool:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![a-z0-9-]){escaped}(?![a-z0-9-])", searchable_text) is not None


def _is_token_covered_by_phrase(token: str, phrases: list[str]) -> bool:
    return any(token in phrase.split() for phrase in phrases)


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def _normalize_optional_label(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.split())
    return normalized or None


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _clamp_score(value: int) -> int:
    return min(100, max(0, value))
