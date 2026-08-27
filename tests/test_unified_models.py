from scholarlead_agent.unified_models import (
    EvidenceRecord,
    UnifiedContact,
    UnifiedFunding,
    UnifiedOrganization,
    UnifiedPaper,
    UnifiedResearcher,
    evidence_records_to_dicts,
)


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        source_name="pubmed",
        source_type="pubmed_lead",
        source_id="lead-1",
        source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        retrieved_at="2026-08-21T10:00:00",
        field_name="pi_full_name",
        field_value="Lei S Qi",
        confidence="medium",
        raw_record_path=None,
        note="candidate lead",
    )


def test_evidence_record_to_dict_has_required_fields() -> None:
    data = make_evidence().to_dict()

    assert data == {
        "source_name": "pubmed",
        "source_type": "pubmed_lead",
        "source_id": "lead-1",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/1/",
        "retrieved_at": "2026-08-21T10:00:00",
        "field_name": "pi_full_name",
        "field_value": "Lei S Qi",
        "confidence": "medium",
        "raw_record_path": None,
        "note": "candidate lead",
    }


def test_unified_models_are_serializable_shells() -> None:
    evidence = make_evidence()

    paper = UnifiedPaper(
        unified_id="paper-doi-10-1-test",
        source_name="crossref",
        source_id="10.1/test",
        doi="10.1/test",
        title="Title",
        abstract="Abstract",
        journal="Journal",
        publisher="Publisher",
        publication_date="2026-01-01",
        publication_year=2026,
        authors=["Alice Smith"],
        organizations=["Example University"],
        source_url="https://doi.org/10.1/test",
        evidence_records=[evidence],
    )
    researcher = UnifiedResearcher(
        unified_id="researcher-1",
        full_name="Alice Smith",
        emails=["alice@example.edu"],
        evidence_records=[evidence],
    )
    organization = UnifiedOrganization(
        unified_id="organization-1",
        name="Example University",
        evidence_records=[evidence],
    )
    funding = UnifiedFunding(
        unified_id="funding-1",
        agency="NIH",
        project_title="Example project",
        evidence_records=[evidence],
    )
    contact = UnifiedContact(
        unified_id="contact-1",
        contact_type="email",
        value="alice@example.edu",
        status="verified_from_source",
        source_url="https://example.edu",
        evidence_records=[evidence],
    )

    assert paper.to_dict()["evidence_records"][0]["field_name"] == "pi_full_name"
    assert researcher.to_dict()["merge_status"] == "not_merged"
    assert organization.to_dict()["name"] == "Example University"
    assert funding.to_dict()["agency"] == "NIH"
    assert contact.to_dict()["contact_type"] == "email"
    assert evidence_records_to_dicts([evidence]) == [evidence.to_dict()]
