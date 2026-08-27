from scholarlead_agent.entity_resolution import resolve_pubmed_leads_to_entities
from scholarlead_agent.pubmed_models import PubMedLead


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
        "country_source": "affiliation_text",
        "raw_affiliation": "Stanford University, Stanford, CA, USA.",
        "matched_keywords": ["CRISPR"],
        "target_service_type": "genome imaging",
        "lead_score": 90,
        "priority": "high",
    }
    values.update(overrides)
    return PubMedLead(**values)


def test_same_verified_email_researchers_are_merged() -> None:
    first = make_lead(lead_id="lead-1", pmid="1")
    second = make_lead(
        lead_id="lead-2",
        pmid="2",
        verified_email="SLQI@stanford.edu",
        recent_publication_title="Second paper",
    )

    result = resolve_pubmed_leads_to_entities(
        [first, second],
        retrieved_at="2026-08-24T12:00:00",
    )

    assert len(result.researchers) == 1
    researcher = result.researchers[0]
    assert researcher.unified_id == "researcher-email-slqi-stanford-edu"
    assert researcher.emails == ["slqi@stanford.edu"]
    assert researcher.source_lead_ids == ["lead-1", "lead-2"]
    assert researcher.related_paper_ids == ["1", "2"]
    assert researcher.merge_status == "merged"
    assert researcher.merge_reason == "verified_email_match"
    assert researcher.match_confidence == "high"


def test_same_name_without_email_is_not_auto_merged() -> None:
    first = make_lead(
        lead_id="lead-1",
        pmid="1",
        verified_email=None,
        email_status="missing",
        name_email_match_confidence="missing",
    )
    second = make_lead(
        lead_id="lead-2",
        pmid="2",
        verified_email=None,
        email_status="missing",
        name_email_match_confidence="missing",
    )

    result = resolve_pubmed_leads_to_entities(
        [first, second],
        retrieved_at="2026-08-24T12:00:00",
    )

    assert len(result.researchers) == 2
    assert {researcher.merge_status for researcher in result.researchers} == {
        "distinct"
    }
    assert len(result.probable_matches) == 1
    assert result.probable_matches[0].reason == "same_name_institution_weak_signal"


def test_same_email_with_conflicting_names_requires_manual_review() -> None:
    first = make_lead(lead_id="lead-1", pi_full_name="Lei S Qi")
    second = make_lead(lead_id="lead-2", pi_full_name="W E Moerner")

    result = resolve_pubmed_leads_to_entities(
        [first, second],
        retrieved_at="2026-08-24T12:00:00",
    )

    assert len(result.researchers) == 1
    assert result.researchers[0].merge_status == "manual_review_required"
    assert result.researchers[0].merge_reason == "same_email_conflicting_identity_fields"
    assert len(result.manual_review_records) == 1


def test_organizations_are_merged_by_normalized_name_and_country() -> None:
    first = make_lead(lead_id="lead-1", institution="Stanford University")
    second = make_lead(lead_id="lead-2", institution="  Stanford   University ")

    result = resolve_pubmed_leads_to_entities(
        [first, second],
        retrieved_at="2026-08-24T12:00:00",
    )

    assert len(result.organizations) == 1
    organization = result.organizations[0]
    assert organization.name == "Stanford University"
    assert organization.country == "United States"
    assert organization.source_record_ids == ["lead-1", "lead-2"]
    assert organization.merge_status == "merged"
    assert organization.merge_reason == "same_normalized_name_country"


def test_contacts_and_evidence_are_traceable() -> None:
    lead = make_lead()

    result = resolve_pubmed_leads_to_entities(
        [lead],
        retrieved_at="2026-08-24T12:00:00",
    )

    assert len(result.contacts) == 1
    assert result.contacts[0].value == "slqi@stanford.edu"
    assert result.contacts[0].status == "verified_from_pubmed_affiliation"
    assert result.contacts[0].evidence_records[0].source_id == lead.lead_id
    assert result.evidence_records
    assert result.to_dict()["researchers"][0]["evidence_records"]
