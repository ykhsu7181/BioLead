"""Converters from source-specific records to unified models."""

from __future__ import annotations

from datetime import datetime
import json
import re
from typing import Any

from scholarlead_agent.crossref_models import CrossrefWork
from scholarlead_agent.nih_reporter_models import NIHFundingRecord
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.unified_models import EvidenceRecord, UnifiedFunding, UnifiedPaper
from scholarlead_agent.works import PaperRecord


def evidence_from_pubmed_lead(
    lead: PubMedLead,
    *,
    retrieved_at: str | None = None,
) -> list[EvidenceRecord]:
    """Convert one PubMed Lead into field-level evidence records."""

    source_url = _first_source_url(lead.source_links) or lead.email_source_url
    base = _EvidenceBase(
        source_name="pubmed",
        source_type="pubmed_lead",
        source_id=lead.lead_id,
        source_url=source_url,
        retrieved_at=retrieved_at or _now_iso(),
        raw_record_path=None,
    )

    records = [
        _evidence(base, "pi_full_name", lead.pi_full_name, "medium"),
        _evidence(base, "email_status", lead.email_status, "high"),
        _evidence(base, "institution", lead.institution, "medium"),
        _evidence(base, "country", lead.country, lead.country_confidence),
        _evidence(
            base,
            "recent_publication_title",
            lead.recent_publication_title,
            "high",
        ),
        _evidence(base, "pmid", lead.pmid, "high"),
        _evidence(base, "doi", lead.doi, "high"),
        _evidence(base, "author_role", lead.author_role, "medium"),
        _evidence(base, "raw_affiliation", lead.raw_affiliation, "high"),
        _evidence(base, "matched_keywords", lead.matched_keywords, "medium"),
        _evidence(base, "target_service_type", lead.target_service_type, "medium"),
        _evidence(base, "lead_score", lead.lead_score, "temporary"),
        _evidence(base, "priority", lead.priority, "temporary"),
    ]
    if lead.verified_email:
        records.append(
            _evidence(
                base,
                "verified_email",
                lead.verified_email,
                lead.name_email_match_confidence,
                note=f"email_source_type={lead.email_source_type}",
            )
        )
    return [record for record in records if record is not None]


def crossref_work_to_unified_paper(
    work: CrossrefWork,
    *,
    retrieved_at: str | None = None,
) -> UnifiedPaper:
    """Convert one Crossref work into a UnifiedPaper."""

    base = _EvidenceBase(
        source_name="crossref",
        source_type="crossref_work",
        source_id=work.crossref_id,
        source_url=work.source_url,
        retrieved_at=retrieved_at or _now_iso(),
        raw_record_path=work.raw_record_path,
    )
    evidence = [
        _evidence(base, "doi", work.doi, "high"),
        _evidence(base, "title", work.title, "high"),
        _evidence(base, "abstract", work.abstract, "medium"),
        _evidence(base, "journal", work.journal, "high"),
        _evidence(base, "publisher", work.publisher, "high"),
        _evidence(base, "publication_date", work.publication_date, "high"),
        _evidence(base, "publication_year", work.publication_year, "high"),
        _evidence(base, "authors", work.authors, "medium"),
        _evidence(base, "funder_names", work.funder_names, "medium"),
        _evidence(base, "reference_count", work.reference_count, "medium"),
        _evidence(
            base,
            "is_referenced_by_count",
            work.is_referenced_by_count,
            "medium",
        ),
    ]

    return UnifiedPaper(
        unified_id=_build_unified_paper_id("crossref", work.doi, work.crossref_id),
        source_name="crossref",
        source_id=work.crossref_id,
        doi=work.doi,
        title=work.title,
        abstract=work.abstract,
        journal=work.journal,
        publisher=work.publisher or None,
        publication_date=work.publication_date,
        publication_year=work.publication_year,
        authors=work.authors,
        organizations=[],
        source_url=work.source_url,
        raw_record_path=work.raw_record_path,
        evidence_records=[record for record in evidence if record is not None],
    )


def openalex_record_to_unified_paper(
    record: PaperRecord,
    *,
    retrieved_at: str | None = None,
    raw_record_path: str | None = None,
) -> UnifiedPaper:
    """Convert the current OpenAlex PaperRecord into a UnifiedPaper draft."""

    base = _EvidenceBase(
        source_name="openalex",
        source_type="openalex_work",
        source_id=record.openalex_id,
        source_url=record.openalex_id,
        retrieved_at=retrieved_at or _now_iso(),
        raw_record_path=raw_record_path,
    )
    publication_year = _extract_year(record.publication_date)
    evidence = [
        _evidence(base, "doi", record.doi, "high"),
        _evidence(base, "title", record.title, "high"),
        _evidence(base, "abstract", record.abstract, "medium"),
        _evidence(base, "publication_date", record.publication_date, "high"),
        _evidence(base, "publication_year", publication_year, "high"),
        _evidence(base, "authors", record.authors, "medium"),
        _evidence(base, "institutions", record.institutions, "medium"),
    ]

    return UnifiedPaper(
        unified_id=_build_unified_paper_id(
            "openalex",
            record.doi,
            record.openalex_id,
        ),
        source_name="openalex",
        source_id=record.openalex_id,
        doi=record.doi,
        title=record.title,
        abstract=record.abstract,
        journal="",
        publisher=None,
        publication_date=record.publication_date,
        publication_year=publication_year,
        authors=record.authors,
        organizations=record.institutions,
        source_url=record.openalex_id,
        raw_record_path=raw_record_path,
        evidence_records=[record for record in evidence if record is not None],
    )


def nih_funding_record_to_unified_funding(
    record: NIHFundingRecord,
    *,
    retrieved_at: str | None = None,
) -> UnifiedFunding:
    """Convert one NIH RePORTER funding record into a UnifiedFunding draft."""

    source_id = record.grant_id or record.project_title
    base = _EvidenceBase(
        source_name="nih_reporter",
        source_type="nih_reporter_project",
        source_id=source_id,
        source_url=record.source_url,
        retrieved_at=retrieved_at or _now_iso(),
        raw_record_path=record.raw_record_path,
    )
    evidence = [
        _evidence(base, "grant_id", record.grant_id, "high"),
        _evidence(base, "agency", record.agency, "high"),
        _evidence(base, "project_title", record.project_title, "high"),
        _evidence(base, "pi_name", record.pi_name, "medium"),
        _evidence(base, "institution", record.institution, "medium"),
        _evidence(base, "fiscal_year", record.fiscal_year, "high"),
        _evidence(base, "project_start", record.project_start, "medium"),
        _evidence(base, "project_end", record.project_end, "medium"),
        _evidence(base, "amount", record.amount, "medium"),
        _evidence(
            base,
            "coverage_note",
            "NIH RePORTER only covers NIH-related funding records.",
            "high",
        ),
    ]

    return UnifiedFunding(
        unified_id=_build_unified_funding_id(record),
        agency=record.agency,
        project_title=record.project_title,
        amount=record.amount,
        fiscal_year=record.fiscal_year,
        source_url=record.source_url,
        evidence_records=[item for item in evidence if item is not None],
    )


class _EvidenceBase:
    def __init__(
        self,
        *,
        source_name: str,
        source_type: str,
        source_id: str,
        source_url: str,
        retrieved_at: str,
        raw_record_path: str | None,
    ) -> None:
        self.source_name = source_name
        self.source_type = source_type
        self.source_id = source_id
        self.source_url = source_url
        self.retrieved_at = retrieved_at
        self.raw_record_path = raw_record_path


def _evidence(
    base: _EvidenceBase,
    field_name: str,
    field_value: Any,
    confidence: str,
    *,
    note: str | None = None,
) -> EvidenceRecord | None:
    value = _serialize_field_value(field_value)
    if value is None:
        return None
    return EvidenceRecord(
        source_name=base.source_name,
        source_type=base.source_type,
        source_id=base.source_id,
        source_url=base.source_url,
        retrieved_at=base.retrieved_at,
        field_name=field_name,
        field_value=value,
        confidence=confidence or "unknown",
        raw_record_path=base.raw_record_path,
        note=note,
    )


def _serialize_field_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, list):
        if not value:
            return None
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _build_unified_paper_id(source_name: str, doi: str | None, source_id: str) -> str:
    if doi:
        return f"paper-doi-{_slug(doi)}"
    return f"paper-{source_name}-{_slug(source_id)}"


def _build_unified_funding_id(record: NIHFundingRecord) -> str:
    if record.grant_id:
        return f"funding-nih-reporter-{_slug(record.grant_id)}-{record.fiscal_year or 'unknown'}"
    return f"funding-nih-reporter-{_slug(record.project_title)}"


def _first_source_url(source_links: list[str]) -> str:
    for link in source_links:
        cleaned = link.strip()
        if cleaned:
            return cleaned
    return ""


def _extract_year(publication_date: str) -> int | None:
    if len(publication_date) < 4:
        return None
    try:
        return int(publication_date[:4])
    except ValueError:
        return None


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower())
    return slug.strip("-") or "unknown"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
