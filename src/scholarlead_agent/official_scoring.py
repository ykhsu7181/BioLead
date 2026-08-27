"""Minimal evidence-backed official scoring for Stage 21F."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from scholarlead_agent.nih_reporter_models import NIHFundingRecord
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.pubmed_scoring import score_publication_recency
from scholarlead_agent.unified_models import EvidenceRecord, UnifiedResearcher


FUNDING_ACTIVITY_DIMENSION = "funding_activity"
RESEARCH_DIRECTION_DIMENSION = "research_direction_match"
PUBLICATION_RECENCY_DIMENSION = "publication_recency"
OUTSOURCING_TENDENCY_DIMENSION = "outsourcing_tendency"


@dataclass(frozen=True)
class OfficialScoringWeights:
    """Centralized official scoring weights for the minimal version."""

    funding_activity: float = 0.4
    research_direction_match: float = 0.3
    publication_recency: float = 0.2
    outsourcing_tendency: float = 0.1

    def to_dict(self) -> dict[str, float]:
        """Convert weights to a serializable dictionary."""

        return asdict(self)


@dataclass(frozen=True)
class PriorityThresholds:
    """Configurable high / medium / low priority thresholds."""

    high: int = 80
    medium: int = 50


@dataclass(frozen=True)
class DimensionScore:
    """One dimension score plus evidence and missing-data reason."""

    name: str
    score: int | None
    weight: float
    reason: str
    evidence_records: list[EvidenceRecord] = field(default_factory=list)
    missing_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the dimension to a serializable dictionary."""

        data = asdict(self)
        data["evidence_records"] = [
            evidence.to_dict() for evidence in self.evidence_records
        ]
        return data


@dataclass(frozen=True)
class OfficialScoreResult:
    """Official four-dimension scoring result for a lead or researcher."""

    subject_id: str
    subject_type: str
    dimensions: dict[str, DimensionScore]
    official_total_score: int | None
    priority: str
    scoring_status: str
    missing_dimensions: list[str]
    score_explanation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert the score result to serializable dictionaries."""

        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "dimensions": {
                name: dimension.to_dict()
                for name, dimension in self.dimensions.items()
            },
            "official_total_score": self.official_total_score,
            "priority": self.priority,
            "scoring_status": self.scoring_status,
            "missing_dimensions": list(self.missing_dimensions),
            "score_explanation": self.score_explanation,
        }


DEFAULT_OFFICIAL_SCORING_WEIGHTS = OfficialScoringWeights()
DEFAULT_PRIORITY_THRESHOLDS = PriorityThresholds()


def score_pubmed_lead_official_minimal(
    lead: PubMedLead,
    *,
    funding_records: list[NIHFundingRecord] | None = None,
    reference_year: int | None = None,
    weights: OfficialScoringWeights = DEFAULT_OFFICIAL_SCORING_WEIGHTS,
    priority_thresholds: PriorityThresholds = DEFAULT_PRIORITY_THRESHOLDS,
    retrieved_at: str = "",
) -> OfficialScoreResult:
    """Score one PubMed Lead with explicit multi-source evidence only."""

    dimensions = {
        FUNDING_ACTIVITY_DIMENSION: _score_funding_activity(
            subject_id=lead.lead_id,
            subject_type="pubmed_lead",
            funding_records=funding_records or [],
            weight=weights.funding_activity,
            retrieved_at=retrieved_at,
        ),
        RESEARCH_DIRECTION_DIMENSION: _score_research_direction_from_lead(
            lead,
            weight=weights.research_direction_match,
            retrieved_at=retrieved_at,
        ),
        PUBLICATION_RECENCY_DIMENSION: _score_publication_recency_from_lead(
            lead,
            reference_year=reference_year,
            weight=weights.publication_recency,
            retrieved_at=retrieved_at,
        ),
        OUTSOURCING_TENDENCY_DIMENSION: _missing_dimension(
            name=OUTSOURCING_TENDENCY_DIMENSION,
            weight=weights.outsourcing_tendency,
            missing_reason=(
                "No explicit outsourcing tendency evidence is connected in Stage 21F."
            ),
        ),
    }
    return _build_official_score_result(
        subject_id=lead.lead_id,
        subject_type="pubmed_lead",
        dimensions=dimensions,
        priority_thresholds=priority_thresholds,
    )


def score_researcher_official_minimal(
    researcher: UnifiedResearcher,
    *,
    funding_records: list[NIHFundingRecord] | None = None,
    research_direction_score: int | None = None,
    publication_year: int | None = None,
    reference_year: int | None = None,
    weights: OfficialScoringWeights = DEFAULT_OFFICIAL_SCORING_WEIGHTS,
    priority_thresholds: PriorityThresholds = DEFAULT_PRIORITY_THRESHOLDS,
    retrieved_at: str = "",
) -> OfficialScoreResult:
    """Score one UnifiedResearcher without guessing missing dimensions."""

    dimensions = {
        FUNDING_ACTIVITY_DIMENSION: _score_funding_activity(
            subject_id=researcher.unified_id,
            subject_type="researcher",
            funding_records=funding_records or [],
            weight=weights.funding_activity,
            retrieved_at=retrieved_at,
        ),
        RESEARCH_DIRECTION_DIMENSION: _score_research_direction_value(
            subject_id=researcher.unified_id,
            subject_type="researcher",
            score=research_direction_score,
            weight=weights.research_direction_match,
            retrieved_at=retrieved_at,
        ),
        PUBLICATION_RECENCY_DIMENSION: _score_publication_recency_value(
            subject_id=researcher.unified_id,
            subject_type="researcher",
            publication_year=publication_year,
            reference_year=reference_year,
            weight=weights.publication_recency,
            retrieved_at=retrieved_at,
        ),
        OUTSOURCING_TENDENCY_DIMENSION: _missing_dimension(
            name=OUTSOURCING_TENDENCY_DIMENSION,
            weight=weights.outsourcing_tendency,
            missing_reason=(
                "No explicit outsourcing tendency evidence is connected in Stage 21F."
            ),
        ),
    }
    return _build_official_score_result(
        subject_id=researcher.unified_id,
        subject_type="researcher",
        dimensions=dimensions,
        priority_thresholds=priority_thresholds,
    )


def assign_official_priority(
    score: int | None,
    *,
    thresholds: PriorityThresholds = DEFAULT_PRIORITY_THRESHOLDS,
) -> str:
    """Assign official priority only when a complete score exists."""

    if score is None:
        return "unscored"
    if score >= thresholds.high:
        return "high"
    if score >= thresholds.medium:
        return "medium"
    return "low"


def _score_funding_activity(
    *,
    subject_id: str,
    subject_type: str,
    funding_records: list[NIHFundingRecord],
    weight: float,
    retrieved_at: str,
) -> DimensionScore:
    if not funding_records:
        return _missing_dimension(
            name=FUNDING_ACTIVITY_DIMENSION,
            weight=weight,
            missing_reason=(
                "No explicit NIH RePORTER funding evidence is attached. "
                "PubMed papers are not used to infer funding activity."
            ),
        )

    current_year = date.today().year
    fiscal_years = [
        record.fiscal_year
        for record in funding_records
        if record.fiscal_year is not None
    ]
    most_recent_year = max(fiscal_years) if fiscal_years else None
    if most_recent_year is None:
        score = 60
        reason = "Explicit funding records exist, but fiscal year is missing."
    elif most_recent_year >= current_year - 2:
        score = 100
        reason = "Explicit recent NIH RePORTER funding evidence is attached."
    else:
        score = 70
        reason = "Explicit older NIH RePORTER funding evidence is attached."

    return DimensionScore(
        name=FUNDING_ACTIVITY_DIMENSION,
        score=score,
        weight=weight,
        reason=reason,
        evidence_records=[
            _funding_evidence(
                record,
                subject_id=subject_id,
                subject_type=subject_type,
                retrieved_at=retrieved_at,
            )
            for record in funding_records
        ],
    )


def _score_research_direction_from_lead(
    lead: PubMedLead,
    *,
    weight: float,
    retrieved_at: str,
) -> DimensionScore:
    return DimensionScore(
        name=RESEARCH_DIRECTION_DIMENSION,
        score=_clamp_score(lead.topic_match_score),
        weight=weight,
        reason=lead.topic_match_reason,
        evidence_records=[
            _lead_evidence(
                lead,
                field_name="matched_keywords",
                field_value=", ".join(lead.matched_keywords),
                confidence="medium",
                retrieved_at=retrieved_at,
                note=lead.topic_match_reason,
            )
        ],
    )


def _score_research_direction_value(
    *,
    subject_id: str,
    subject_type: str,
    score: int | None,
    weight: float,
    retrieved_at: str,
) -> DimensionScore:
    if score is None:
        return _missing_dimension(
            name=RESEARCH_DIRECTION_DIMENSION,
            weight=weight,
            missing_reason="No explicit research direction match score is attached.",
        )
    clamped = _clamp_score(score)
    return DimensionScore(
        name=RESEARCH_DIRECTION_DIMENSION,
        score=clamped,
        weight=weight,
        reason="Explicit research direction match score provided by deterministic rules.",
        evidence_records=[
            _generic_evidence(
                source_type=subject_type,
                source_id=subject_id,
                field_name="research_direction_score",
                field_value=str(clamped),
                confidence="medium",
                retrieved_at=retrieved_at,
            )
        ],
    )


def _score_publication_recency_from_lead(
    lead: PubMedLead,
    *,
    reference_year: int | None,
    weight: float,
    retrieved_at: str,
) -> DimensionScore:
    return _score_publication_recency_value(
        subject_id=lead.lead_id,
        subject_type="pubmed_lead",
        publication_year=lead.publication_year,
        reference_year=reference_year,
        weight=weight,
        retrieved_at=retrieved_at,
    )


def _score_publication_recency_value(
    *,
    subject_id: str,
    subject_type: str,
    publication_year: int | None,
    reference_year: int | None,
    weight: float,
    retrieved_at: str,
) -> DimensionScore:
    if publication_year is None:
        return _missing_dimension(
            name=PUBLICATION_RECENCY_DIMENSION,
            weight=weight,
            missing_reason="No publication year evidence is attached.",
        )

    score = score_publication_recency(
        publication_year,
        reference_year=reference_year,
    )
    return DimensionScore(
        name=PUBLICATION_RECENCY_DIMENSION,
        score=score,
        weight=weight,
        reason=f"Publication year evidence: {publication_year}.",
        evidence_records=[
            _generic_evidence(
                source_type=subject_type,
                source_id=subject_id,
                field_name="publication_year",
                field_value=str(publication_year),
                confidence="high",
                retrieved_at=retrieved_at,
            )
        ],
    )


def _build_official_score_result(
    *,
    subject_id: str,
    subject_type: str,
    dimensions: dict[str, DimensionScore],
    priority_thresholds: PriorityThresholds,
) -> OfficialScoreResult:
    missing_dimensions = [
        name for name, dimension in dimensions.items() if dimension.score is None
    ]
    if missing_dimensions:
        total_score = None
        scoring_status = "partial_missing_data"
    else:
        total_score = round(
            sum((dimension.score or 0) * dimension.weight for dimension in dimensions.values())
        )
        scoring_status = "complete"

    priority = assign_official_priority(total_score, thresholds=priority_thresholds)
    explanation = _build_score_explanation(
        total_score=total_score,
        priority=priority,
        scoring_status=scoring_status,
        missing_dimensions=missing_dimensions,
    )
    return OfficialScoreResult(
        subject_id=subject_id,
        subject_type=subject_type,
        dimensions=dimensions,
        official_total_score=total_score,
        priority=priority,
        scoring_status=scoring_status,
        missing_dimensions=missing_dimensions,
        score_explanation=explanation,
    )


def _missing_dimension(
    *,
    name: str,
    weight: float,
    missing_reason: str,
) -> DimensionScore:
    return DimensionScore(
        name=name,
        score=None,
        weight=weight,
        reason=missing_reason,
        evidence_records=[],
        missing_reason=missing_reason,
    )


def _build_score_explanation(
    *,
    total_score: int | None,
    priority: str,
    scoring_status: str,
    missing_dimensions: list[str],
) -> str:
    if total_score is None:
        return (
            "Official four-dimension scoring is incomplete because evidence is "
            f"missing for: {', '.join(missing_dimensions)}. "
            f"scoring_status={scoring_status}, priority={priority}."
        )
    return (
        "Official four-dimension score calculated from explicit evidence: "
        f"official_total_score={total_score}, priority={priority}."
    )


def _funding_evidence(
    record: NIHFundingRecord,
    *,
    subject_id: str,
    subject_type: str,
    retrieved_at: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_name="nih_reporter",
        source_type="nih_reporter_project",
        source_id=record.grant_id,
        source_url=record.source_url,
        retrieved_at=retrieved_at,
        field_name="funding_activity",
        field_value=(
            f"{record.agency} | {record.project_title} | "
            f"FY {record.fiscal_year or 'unknown'}"
        ),
        confidence="high",
        raw_record_path=record.raw_record_path,
        note=f"attached_to={subject_type}:{subject_id}",
    )


def _lead_evidence(
    lead: PubMedLead,
    *,
    field_name: str,
    field_value: str,
    confidence: str,
    retrieved_at: str,
    note: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_name="pubmed",
        source_type="pubmed_lead",
        source_id=lead.lead_id,
        source_url=lead.source_links[0] if lead.source_links else lead.email_source_url,
        retrieved_at=retrieved_at,
        field_name=field_name,
        field_value=field_value,
        confidence=confidence,
        raw_record_path=None,
        note=note,
    )


def _generic_evidence(
    *,
    source_type: str,
    source_id: str,
    field_name: str,
    field_value: str,
    confidence: str,
    retrieved_at: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        source_name="scholarlead_agent",
        source_type=source_type,
        source_id=source_id,
        source_url="",
        retrieved_at=retrieved_at,
        field_name=field_name,
        field_value=field_value,
        confidence=confidence,
    )


def _clamp_score(value: int) -> int:
    return min(100, max(0, value))
