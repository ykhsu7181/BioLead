import json

from scholarlead_agent.crossref_models import CrossrefWork
from scholarlead_agent.nih_reporter_models import NIHFundingRecord
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.unified_converters import (
    crossref_work_to_unified_paper,
    evidence_from_pubmed_lead,
    nih_funding_record_to_unified_funding,
    openalex_record_to_unified_paper,
)
from scholarlead_agent.works import PaperRecord


def make_pubmed_lead(**overrides) -> PubMedLead:
    values = {
        "lead_id": "pubmed-41951915-lei-s-qi",
        "pi_full_name": "Lei S Qi",
        "verified_email": "slqi@stanford.edu",
        "email_status": "verified_from_pubmed_affiliation",
        "email_source_url": "https://pubmed.ncbi.nlm.nih.gov/41951915/",
        "email_source_type": "pubmed_affiliation",
        "name_email_match_confidence": "high",
        "institution": "Stanford University",
        "country": "United States",
        "country_confidence": "high",
        "recent_publication_title": (
            "CRISPR-Cas-based live cell imaging of genome dynamics"
        ),
        "abstract": "Abstract text.",
        "journal": "Nature Methods",
        "publication_year": 2026,
        "pmid": "41951915",
        "doi": "10.1038/example",
        "author_role": "email_author",
        "source_links": ["https://pubmed.ncbi.nlm.nih.gov/41951915/"],
        "data_quality": "email_evidence_available",
        "manual_review_required": False,
        "notes": "Email found in PubMed affiliation.",
        "country_source": "affiliation_text",
        "raw_affiliation": "Stanford University, Stanford, CA, USA. slqi@stanford.edu.",
        "matched_keywords": ["CRISPR", "genome imaging"],
        "target_service_type": "genome imaging",
        "lead_score": 90,
        "priority": "high",
    }
    values.update(overrides)
    return PubMedLead(**values)


def test_pubmed_lead_converts_to_basic_evidence_records() -> None:
    records = evidence_from_pubmed_lead(
        make_pubmed_lead(),
        retrieved_at="2026-08-21T10:00:00",
    )
    by_field = {record.field_name: record for record in records}

    assert by_field["pi_full_name"].source_name == "pubmed"
    assert by_field["pi_full_name"].source_type == "pubmed_lead"
    assert by_field["pi_full_name"].field_value == "Lei S Qi"
    assert by_field["verified_email"].field_value == "slqi@stanford.edu"
    assert by_field["verified_email"].confidence == "high"
    assert by_field["country"].confidence == "high"
    assert by_field["lead_score"].confidence == "temporary"
    assert json.loads(by_field["matched_keywords"].field_value) == [
        "CRISPR",
        "genome imaging",
    ]


def test_pubmed_lead_without_email_does_not_create_verified_email_evidence() -> None:
    records = evidence_from_pubmed_lead(
        make_pubmed_lead(verified_email=None, email_status="missing"),
        retrieved_at="2026-08-21T10:00:00",
    )

    assert "verified_email" not in {record.field_name for record in records}
    assert "email_status" in {record.field_name for record in records}


def test_crossref_work_converts_to_unified_paper() -> None:
    work = CrossrefWork(
        source="crossref",
        crossref_id="10.1038/example",
        doi="10.1038/example",
        title="CRISPR imaging in cancer",
        abstract="Abstract text.",
        journal="Nature",
        publisher="Springer Nature",
        publication_date="2026-05-02",
        publication_year=2026,
        authors=["Lei S Qi"],
        funder_names=["National Institutes of Health"],
        reference_count=12,
        is_referenced_by_count=34,
        source_url="https://doi.org/10.1038/example",
        raw_record_path="data/raw/crossref/example.json",
    )

    paper = crossref_work_to_unified_paper(
        work,
        retrieved_at="2026-08-21T10:00:00",
    )
    evidence_by_field = {record.field_name: record for record in paper.evidence_records}

    assert paper.unified_id == "paper-doi-10-1038-example"
    assert paper.source_name == "crossref"
    assert paper.doi == "10.1038/example"
    assert paper.title == "CRISPR imaging in cancer"
    assert paper.publisher == "Springer Nature"
    assert paper.organizations == []
    assert evidence_by_field["funder_names"].field_value == (
        '["National Institutes of Health"]'
    )
    assert evidence_by_field["funder_names"].confidence == "medium"


def test_openalex_record_converts_to_unified_paper_draft() -> None:
    record = PaperRecord(
        openalex_id="https://openalex.org/W123",
        doi="10.1101/example",
        title="Single-cell cancer atlas",
        abstract="Abstract text.",
        publication_date="2025-03-04",
        authors=["Alice Smith", "Bob Jones"],
        institutions=["Example University"],
    )

    paper = openalex_record_to_unified_paper(
        record,
        retrieved_at="2026-08-21T10:00:00",
        raw_record_path="data/raw/openalex/example.json",
    )
    evidence_by_field = {record.field_name: record for record in paper.evidence_records}

    assert paper.unified_id == "paper-doi-10-1101-example"
    assert paper.source_name == "openalex"
    assert paper.source_id == "https://openalex.org/W123"
    assert paper.journal == ""
    assert paper.publisher is None
    assert paper.publication_year == 2025
    assert paper.organizations == ["Example University"]
    assert evidence_by_field["institutions"].field_value == '["Example University"]'
    assert evidence_by_field["publication_year"].field_value == "2025"


def test_nih_funding_record_converts_to_unified_funding() -> None:
    record = NIHFundingRecord(
        source="nih_reporter",
        grant_id="R01CA123456",
        agency="NCI",
        project_title="CRISPR imaging of cancer cells",
        pi_name="Lei S Qi",
        institution="Stanford University",
        fiscal_year=2026,
        project_start="2025-07-01",
        project_end="2027-06-30",
        amount=250000.0,
        source_url="https://reporter.nih.gov/project-details/123456",
        raw_record_path="data/raw/nih_reporter/sample.json",
    )

    funding = nih_funding_record_to_unified_funding(
        record,
        retrieved_at="2026-08-24T10:00:00",
    )
    evidence_by_field = {
        record.field_name: record for record in funding.evidence_records
    }

    assert funding.unified_id == "funding-nih-reporter-r01ca123456-2026"
    assert funding.agency == "NCI"
    assert funding.project_title == "CRISPR imaging of cancer cells"
    assert funding.amount == 250000.0
    assert evidence_by_field["grant_id"].confidence == "high"
    assert evidence_by_field["pi_name"].confidence == "medium"
    assert evidence_by_field["institution"].field_value == "Stanford University"
    assert evidence_by_field["coverage_note"].field_value.startswith(
        "NIH RePORTER only covers"
    )
