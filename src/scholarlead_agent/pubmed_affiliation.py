"""Basic PubMed affiliation country and institution identification."""

from __future__ import annotations

from dataclasses import dataclass, replace
import re

from scholarlead_agent.pubmed_models import PubMedLead


UNKNOWN_COUNTRY = "unknown"
UNKNOWN_CONFIDENCE = "unknown"
UNKNOWN_SOURCE = "unknown"
AFFILIATION_TEXT_SOURCE = "affiliation_text"
EMAIL_DOMAIN_SOURCE = "email_domain_auxiliary"

EMAIL_PATTERN = re.compile(
    r"(?<![A-Za-z0-9._%+-])"
    r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    r"(?![A-Za-z0-9._%+-])"
)

INSTITUTION_KEYWORD_PRIORITY = [
    "university",
    "institute",
    "hospital",
    "college",
    "academy",
    "school",
    "centre",
    "center",
    "laboratory",
    "lab",
    "department",
]

EMAIL_DOMAIN_COUNTRY_HINTS = [
    (".ac.uk", "United Kingdom"),
    (".edu", "United States"),
    (".cn", "China"),
    (".jp", "Japan"),
    (".de", "Germany"),
    (".fr", "France"),
    (".ca", "Canada"),
    (".au", "Australia"),
]

COUNTRY_ONLY_ALIASES = {
    "united states",
    "united states of america",
    "usa",
    "u s a",
    "us",
    "u s",
    "united kingdom",
    "uk",
    "u k",
    "england",
    "scotland",
    "wales",
    "china",
    "pr china",
    "p r china",
    "peoples republic of china",
    "people s republic of china",
    "japan",
    "germany",
    "france",
    "canada",
    "australia",
}


@dataclass(frozen=True)
class CountryIdentification:
    """Country identification result with confidence and source."""

    country: str
    country_confidence: str
    country_source: str


@dataclass(frozen=True)
class AffiliationIdentification:
    """Structured affiliation information retained on a PubMed lead."""

    institution: str | None
    country: str
    country_confidence: str
    country_source: str
    raw_affiliation: str | None


def normalize_affiliation_text(raw_affiliation: str | None) -> str:
    """Normalize whitespace in affiliation text for deterministic matching."""

    if raw_affiliation is None:
        return ""
    return " ".join(raw_affiliation.split())


def identify_country_from_affiliation(
    raw_affiliation: str | None,
    *,
    email: str | None = None,
) -> CountryIdentification:
    """Identify country from affiliation text, with email domain as auxiliary only."""

    normalized = normalize_affiliation_text(raw_affiliation)
    if normalized:
        country = _match_country_in_affiliation(normalized)
        if country:
            return CountryIdentification(
                country=country,
                country_confidence="high",
                country_source=AFFILIATION_TEXT_SOURCE,
            )

    domain_country = _match_country_from_email_domain(email)
    if domain_country:
        return CountryIdentification(
            country=domain_country,
            country_confidence="medium",
            country_source=EMAIL_DOMAIN_SOURCE,
        )

    return CountryIdentification(
        country=UNKNOWN_COUNTRY,
        country_confidence=UNKNOWN_CONFIDENCE,
        country_source=UNKNOWN_SOURCE,
    )


def identify_institution_from_affiliation(raw_affiliation: str | None) -> str | None:
    """Identify a likely institution name from a PubMed affiliation string."""

    normalized = normalize_affiliation_text(raw_affiliation)
    if not normalized:
        return None

    candidates = _clean_affiliation_segments(normalized)
    if not candidates:
        return None

    best_candidate = _select_best_institution_candidate(candidates)
    return best_candidate or candidates[0]


def parse_affiliation(
    raw_affiliation: str | None,
    *,
    email: str | None = None,
) -> AffiliationIdentification:
    """Parse affiliation text into institution and country fields."""

    raw_value = raw_affiliation if raw_affiliation and raw_affiliation.strip() else None
    country = identify_country_from_affiliation(raw_value, email=email)
    return AffiliationIdentification(
        institution=identify_institution_from_affiliation(raw_value),
        country=country.country,
        country_confidence=country.country_confidence,
        country_source=country.country_source,
        raw_affiliation=raw_value,
    )


def enrich_lead_affiliation(lead: PubMedLead) -> PubMedLead:
    """Return a lead with institution, country, and raw affiliation fields filled."""

    affiliation = parse_affiliation(
        lead.raw_affiliation or lead.institution,
        email=lead.verified_email,
    )
    return replace(
        lead,
        institution=affiliation.institution,
        country=affiliation.country,
        country_confidence=affiliation.country_confidence,
        country_source=affiliation.country_source,
        raw_affiliation=affiliation.raw_affiliation,
    )


def enrich_leads_affiliation(leads: list[PubMedLead]) -> list[PubMedLead]:
    """Return leads with basic affiliation enrichment applied."""

    return [enrich_lead_affiliation(lead) for lead in leads]


def _match_country_in_affiliation(affiliation: str) -> str | None:
    phrase_rules = [
        ("United States", r"\bUnited States(?: of America)?\b"),
        ("United Kingdom", r"\bUnited Kingdom\b"),
        ("United Kingdom", r"\bEngland\b"),
        ("United Kingdom", r"\bScotland\b"),
        ("United Kingdom", r"\bWales\b"),
        ("China", r"\bPeople'?s Republic of China\b"),
        ("China", r"\bP\.?\s*R\.?\s*China\b"),
        ("China", r"\bPR China\b"),
        ("China", r"\bChina\b"),
        ("Japan", r"\bJapan\b"),
        ("Germany", r"\bGermany\b"),
        ("France", r"\bFrance\b"),
        ("Canada", r"\bCanada\b"),
        ("Australia", r"\bAustralia\b"),
    ]
    for country, pattern in phrase_rules:
        if re.search(pattern, affiliation, flags=re.IGNORECASE):
            return country

    acronym_rules = [
        ("United States", r"(?<![A-Za-z])U\.?\s*S\.?\s*A\.?(?![A-Za-z])"),
        ("United States", r"(?<![A-Za-z])U\.?\s*S\.?(?![A-Za-z])"),
        ("United Kingdom", r"(?<![A-Za-z])U\.?\s*K\.?(?![A-Za-z])"),
    ]
    for country, pattern in acronym_rules:
        if re.search(pattern, affiliation):
            return country

    return None


def _match_country_from_email_domain(email: str | None) -> str | None:
    if not email:
        return None

    match = EMAIL_PATTERN.fullmatch(email.strip())
    if match is None:
        return None

    domain = match.group(1).split("@", maxsplit=1)[1].lower().rstrip(".")
    for suffix, country in EMAIL_DOMAIN_COUNTRY_HINTS:
        if domain.endswith(suffix):
            return country
    return None


def _clean_affiliation_segments(affiliation: str) -> list[str]:
    affiliation_without_email = EMAIL_PATTERN.sub("", affiliation)
    raw_segments = re.split(r"[,;]", affiliation_without_email)
    segments: list[str] = []

    for segment in raw_segments:
        cleaned = _clean_institution_segment(segment)
        if not cleaned or _is_country_only_segment(cleaned):
            continue
        segments.append(cleaned)

    return _deduplicate_preserving_order(segments)


def _clean_institution_segment(segment: str) -> str:
    cleaned = segment.strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _is_country_only_segment(segment: str) -> bool:
    normalized = re.sub(r"[^A-Za-z]+", " ", segment).lower()
    normalized = " ".join(normalized.split())
    return normalized in COUNTRY_ONLY_ALIASES


def _select_best_institution_candidate(candidates: list[str]) -> str | None:
    lowered_candidates = [(candidate, candidate.lower()) for candidate in candidates]
    for keyword in INSTITUTION_KEYWORD_PRIORITY:
        for candidate, lowered in lowered_candidates:
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return candidate
    return None


def _deduplicate_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for value in values:
        lookup = value.lower()
        if lookup in seen:
            continue
        seen.add(lookup)
        results.append(value)

    return results
