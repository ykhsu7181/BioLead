"""Models and validation helpers for PubMed collection."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


PUBMED_MAX_RESULTS_LIMIT = 100


@dataclass(frozen=True)
class PubMedSearchParams:
    """Validated parameters for a PubMed first-round search."""

    query: str
    from_date: str
    to_date: str
    max_results: int
    country: str | None = None
    service_type: str | None = None
    raw_dir: Path = Path("data/raw/pubmed")
    processed_dir: Path = Path("data/processed/pubmed")


@dataclass(frozen=True)
class PubMedAuthor:
    """Structured author information parsed from PubMed XML."""

    full_name: str
    last_name: str
    fore_name: str
    initials: str
    author_position: int
    is_last_author: bool
    affiliations: list[str]


@dataclass(frozen=True)
class PubMedPaper:
    """Structured paper information parsed from PubMed XML."""

    source: str
    pmid: str
    doi: str | None
    title: str
    abstract: str
    journal: str
    publication_date: str
    publication_year: int | None
    article_types: list[str]
    mesh_terms: list[str]
    keywords: list[str]
    authors: list[PubMedAuthor]
    affiliations: list[str]
    source_url: str
    raw_record_path: str | None = None


@dataclass(frozen=True)
class PubMedEmailEvidence:
    """Evidence for an email address found in PubMed affiliation text."""

    email: str | None
    email_status: str
    email_source_type: str
    email_source_url: str
    matched_author_name: str | None
    matched_affiliation: str | None
    name_email_match_confidence: str
    email_reason: str | None = None


@dataclass(frozen=True)
class PubMedLead:
    """Candidate customer lead generated from PubMed-only evidence."""

    lead_id: str
    pi_full_name: str
    verified_email: str | None
    email_status: str
    email_source_url: str
    email_source_type: str
    name_email_match_confidence: str
    institution: str | None
    country: str
    country_confidence: str
    recent_publication_title: str
    abstract: str
    journal: str
    publication_year: int | None
    pmid: str
    doi: str | None
    author_role: str
    source_links: list[str]
    data_quality: str
    manual_review_required: bool
    notes: str
    merge_status: str = "not_merged"
    merge_reason: str | None = None
    country_source: str = "unknown"
    raw_affiliation: str | None = None
    matched_keywords: list[str] = field(default_factory=list)
    target_service_type: str | None = None
    topic_match_score: int = 0
    topic_match_reason: str = (
        "No matched keywords. default rule / pending client keyword hierarchy."
    )
    publication_recency_score: int = 0
    email_contactability_score: int = 0
    lead_score: int = 0
    priority: str = "unscored"
    score_explanation: str = "Not scored."
    funding_activity_score: int | None = None
    funding_activity_reason: str = (
        "Funding source not connected in PubMed-only first round"
    )
    outsourcing_tendency_score: int | None = None
    official_scoring_status: str = "pending_multi_source_data"


def validate_pubmed_search_inputs(
    *,
    query: str,
    from_date: str,
    to_date: str,
    max_results: int,
    country: str | None = None,
    service_type: str | None = None,
    raw_dir: Path | str = Path("data/raw/pubmed"),
    processed_dir: Path | str = Path("data/processed/pubmed"),
) -> PubMedSearchParams:
    """Validate CLI inputs for the PubMed first-round workflow."""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query cannot be empty")

    parsed_from_date = _parse_date(from_date, "from_date")
    parsed_to_date = _parse_date(to_date, "to_date")
    if parsed_from_date > parsed_to_date:
        raise ValueError("from_date must be earlier than or equal to to_date")

    if max_results < 1 or max_results > PUBMED_MAX_RESULTS_LIMIT:
        raise ValueError(
            f"max_results must be between 1 and {PUBMED_MAX_RESULTS_LIMIT}"
        )

    normalized_country = _normalize_optional_text(country)
    if normalized_country is not None:
        normalized_country = normalized_country.upper()

    return PubMedSearchParams(
        query=normalized_query,
        from_date=from_date,
        to_date=to_date,
        max_results=max_results,
        country=normalized_country,
        service_type=_normalize_optional_text(service_type),
        raw_dir=Path(raw_dir),
        processed_dir=Path(processed_dir),
    )


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must be in YYYY-MM-DD format") from error


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    return normalized
