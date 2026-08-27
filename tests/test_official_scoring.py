from scholarlead_agent.nih_reporter_models import NIHFundingRecord
from scholarlead_agent.official_scoring import (
    DEFAULT_OFFICIAL_SCORING_WEIGHTS,
    FUNDING_ACTIVITY_DIMENSION,
    OUTSOURCING_TENDENCY_DIMENSION,
    PUBLICATION_RECENCY_DIMENSION,
    RESEARCH_DIRECTION_DIMENSION,
    PriorityThresholds,
    assign_official_priority,
    score_pubmed_lead_official_minimal,
    score_researcher_official_minimal,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.unified_models import UnifiedResearcher


def make_lead(**overrides) -> PubMedLead:
    values = {
        "lead_id": "pubmed-1-lei-s-qi",
        "pi_full_name": "Lei S Qi",
        "verified_email": "slqi@stanford.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "email_source_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
        "email_source_type": "pubmed_affiliation",
        "name_email_match_confidence": "high",
        "institution": "Stanford University",
        "country": "United States",
        "country_confidence": "high",
        "recent_publication_title": "CRISPR imaging",
        "abstract": "Abstract text.",
        "journal": "Nature Methods",
        "publication_year": 2026,
        "pmid": "1",
        "doi": "10.1038/example",
        "author_role": "email_author",
        "source_links": ["https://pubmed.ncbi.nlm.nih.gov/1/"],
        "data_quality": "email_evidence_available",
        "manual_review_required": False,
        "notes": "Email found in PubMed affiliation.",
        "matched_keywords": ["CRISPR"],
        "topic_match_score": 80,
        "topic_match_reason": "Matched keywords: CRISPR.",
    }
    values.update(overrides)
    return PubMedLead(**values)


def make_funding(**overrides) -> NIHFundingRecord:
    values = {
        "source": "nih_reporter",
        "grant_id": "R01CA123456",
        "agency": "NCI",
        "project_title": "CRISPR imaging of cancer cells",
        "pi_name": "Lei S Qi",
        "institution": "Stanford University",
        "fiscal_year": 2026,
        "project_start": "2025-07-01",
        "project_end": "2027-06-30",
        "amount": 250000.0,
        "source_url": "https://reporter.nih.gov/project-details/123456",
        "raw_record_path": "data/raw/nih_reporter/sample.json",
    }
    values.update(overrides)
    return NIHFundingRecord(**values)


def test_official_weights_are_centralized() -> None:
    assert DEFAULT_OFFICIAL_SCORING_WEIGHTS.to_dict() == {
        "funding_activity": 0.4,
        "research_direction_match": 0.3,
        "publication_recency": 0.2,
        "outsourcing_tendency": 0.1,
    }


def test_official_scoring_keeps_missing_funding_and_outsourcing_unscored() -> None:
    result = score_pubmed_lead_official_minimal(
        make_lead(),
        reference_year=2026,
        retrieved_at="2026-08-24T12:00:00",
    )

    assert result.official_total_score is None
    assert result.priority == "unscored"
    assert result.scoring_status == "partial_missing_data"
    assert result.missing_dimensions == [
        FUNDING_ACTIVITY_DIMENSION,
        OUTSOURCING_TENDENCY_DIMENSION,
    ]
    assert result.dimensions[FUNDING_ACTIVITY_DIMENSION].score is None
    assert "PubMed papers are not used to infer funding" in (
        result.dimensions[FUNDING_ACTIVITY_DIMENSION].missing_reason or ""
    )
    assert result.dimensions[OUTSOURCING_TENDENCY_DIMENSION].score is None


def test_official_scoring_uses_explicit_funding_evidence_only() -> None:
    result = score_pubmed_lead_official_minimal(
        make_lead(),
        funding_records=[make_funding()],
        reference_year=2026,
        retrieved_at="2026-08-24T12:00:00",
    )

    funding = result.dimensions[FUNDING_ACTIVITY_DIMENSION]
    assert funding.score == 100
    assert funding.evidence_records[0].source_name == "nih_reporter"
    assert funding.evidence_records[0].source_id == "R01CA123456"
    assert result.dimensions[RESEARCH_DIRECTION_DIMENSION].score == 80
    assert result.dimensions[PUBLICATION_RECENCY_DIMENSION].score == 100
    assert result.official_total_score is None
    assert result.missing_dimensions == [OUTSOURCING_TENDENCY_DIMENSION]


def test_complete_official_score_gets_priority_when_all_dimensions_have_scores() -> None:
    result = score_pubmed_lead_official_minimal(
        make_lead(),
        funding_records=[make_funding()],
        reference_year=2026,
        retrieved_at="2026-08-24T12:00:00",
    )
    dimensions = dict(result.dimensions)
    dimensions[OUTSOURCING_TENDENCY_DIMENSION] = dimensions[
        OUTSOURCING_TENDENCY_DIMENSION
    ].__class__(
        name=OUTSOURCING_TENDENCY_DIMENSION,
        score=60,
        weight=0.1,
        reason="Explicit outsourcing signal supplied in test.",
        evidence_records=[],
    )
    rebuilt = result.__class__(
        subject_id=result.subject_id,
        subject_type=result.subject_type,
        dimensions=dimensions,
        official_total_score=88,
        priority=assign_official_priority(88),
        scoring_status="complete",
        missing_dimensions=[],
        score_explanation="complete",
    )

    assert rebuilt.priority == "high"
    assert assign_official_priority(49) == "low"
    assert assign_official_priority(50) == "medium"
    assert assign_official_priority(80) == "high"
    assert assign_official_priority(None) == "unscored"


def test_priority_thresholds_are_configurable() -> None:
    thresholds = PriorityThresholds(high=90, medium=70)

    assert assign_official_priority(89, thresholds=thresholds) == "medium"
    assert assign_official_priority(69, thresholds=thresholds) == "low"


def test_researcher_official_score_does_not_guess_missing_values() -> None:
    researcher = UnifiedResearcher(
        unified_id="researcher-email-slqi-stanford-edu",
        full_name="Lei S Qi",
        emails=["slqi@stanford.edu"],
    )

    result = score_researcher_official_minimal(
        researcher,
        funding_records=[],
        research_direction_score=None,
        publication_year=None,
        retrieved_at="2026-08-24T12:00:00",
    )

    assert result.subject_type == "researcher"
    assert result.official_total_score is None
    assert set(result.missing_dimensions) == {
        FUNDING_ACTIVITY_DIMENSION,
        RESEARCH_DIRECTION_DIMENSION,
        PUBLICATION_RECENCY_DIMENSION,
        OUTSOURCING_TENDENCY_DIMENSION,
    }
