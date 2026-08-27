"""Minimal unified data models for multi-source expansion."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceMetadata:
    """Required source-level metadata for every external data record."""

    source_name: str
    source_record_id: str
    source_url: str
    raw_file_path: str | None
    collected_at: str
    parser_version: str
    converter_version: str
    confidence: str
    license_or_terms_note: str
    rate_limit_note: str | None = None
    access_restriction_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to a serializable dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class EvidenceRecord:
    """Traceable evidence for one normalized field."""

    source_name: str
    source_type: str
    source_id: str
    source_url: str
    retrieved_at: str
    field_name: str
    field_value: str
    confidence: str
    raw_record_path: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert evidence to a serializable dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class UnifiedPaper:
    """Source-neutral paper metadata used for later multi-source merging."""

    unified_id: str
    source_name: str
    source_id: str
    doi: str | None
    title: str
    abstract: str
    journal: str
    publisher: str | None
    publication_date: str
    publication_year: int | None
    authors: list[str]
    organizations: list[str]
    source_url: str
    raw_record_path: str | None = None
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the unified paper to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


@dataclass(frozen=True)
class UnifiedResearcher:
    """Minimal source-neutral researcher shell for later entity resolution."""

    unified_id: str
    full_name: str
    emails: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    country: str | None = None
    source_ids: dict[str, str] = field(default_factory=dict)
    source_lead_ids: list[str] = field(default_factory=list)
    related_paper_ids: list[str] = field(default_factory=list)
    funding_ids: list[str] = field(default_factory=list)
    merge_status: str = "not_merged"
    merge_reason: str | None = None
    match_confidence: str = "unknown"
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the unified researcher to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


@dataclass(frozen=True)
class UnifiedOrganization:
    """Minimal source-neutral organization shell."""

    unified_id: str
    name: str
    country: str | None = None
    source_ids: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    source_record_ids: list[str] = field(default_factory=list)
    merge_status: str = "not_merged"
    merge_reason: str | None = None
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the unified organization to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


@dataclass(frozen=True)
class UnifiedFunding:
    """Minimal source-neutral funding shell for future funding sources."""

    unified_id: str
    agency: str
    project_title: str
    amount: float | None = None
    fiscal_year: int | None = None
    source_url: str | None = None
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the unified funding record to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


@dataclass(frozen=True)
class UnifiedContact:
    """Minimal source-neutral contact shell."""

    unified_id: str
    contact_type: str
    value: str
    status: str
    source_url: str
    evidence_records: list[EvidenceRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert the unified contact to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


def evidence_records_to_dicts(
    evidence_records: list[EvidenceRecord],
) -> list[dict[str, Any]]:
    """Convert evidence records to dictionaries."""

    return [record.to_dict() for record in evidence_records]
