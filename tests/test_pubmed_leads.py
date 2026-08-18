from scholarlead_agent.pubmed_affiliation import (
    enrich_lead_affiliation,
    identify_country_from_affiliation,
    identify_institution_from_affiliation,
    parse_affiliation,
)
from scholarlead_agent.pubmed_leads import (
    build_leads_from_paper,
    build_leads_from_papers,
    deduplicate_pubmed_leads,
    extract_email_evidence_from_paper,
    extract_valid_emails_from_text,
    get_pubmed_lead_strong_dedup_key,
    is_valid_email,
)
from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedLead, PubMedPaper


def make_author(
    *,
    full_name: str,
    position: int,
    is_last_author: bool = False,
    affiliations: list[str] | None = None,
) -> PubMedAuthor:
    first, _, last = full_name.partition(" ")
    return PubMedAuthor(
        full_name=full_name,
        last_name=last,
        fore_name=first,
        initials=first[:1],
        author_position=position,
        is_last_author=is_last_author,
        affiliations=affiliations or [],
    )


def make_paper(authors: list[PubMedAuthor], affiliations: list[str] | None = None) -> PubMedPaper:
    return PubMedPaper(
        source="pubmed",
        pmid="12345678",
        doi="10.1000/abc",
        title="A title",
        abstract="An abstract",
        journal="A journal",
        publication_date="2024-01-01",
        publication_year=2024,
        article_types=[],
        mesh_terms=[],
        keywords=[],
        authors=authors,
        affiliations=affiliations or [
            affiliation
            for author in authors
            for affiliation in author.affiliations
        ],
        source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
    )


def test_extract_valid_emails_from_text_normalizes_and_deduplicates() -> None:
    emails = extract_valid_emails_from_text(
        "Contact John.Smith@Example.edu or john.smith@example.edu."
    )

    assert emails == ["john.smith@example.edu"]


def test_is_valid_email_rejects_incomplete_email() -> None:
    assert is_valid_email("alice@example.edu") is True
    assert is_valid_email("alice@example") is False


def test_extract_email_evidence_marks_single_author_affiliation_as_high_confidence() -> None:
    author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=[
            "Department of Biology, Example University, john.smith@example.edu"
        ],
    )
    paper = make_paper([author])

    evidence = extract_email_evidence_from_paper(paper)

    assert len(evidence) == 1
    item = evidence[0]
    assert item.email == "john.smith@example.edu"
    assert item.email_status == "verified_from_pubmed_affiliation"
    assert item.email_source_type == "pubmed_affiliation"
    assert item.email_source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert item.matched_author_name == "John Smith"
    assert item.matched_affiliation == (
        "Department of Biology, Example University, john.smith@example.edu"
    )
    assert item.name_email_match_confidence == "high"
    assert item.email_reason is None


def test_extract_email_evidence_marks_shared_affiliation_as_medium_confidence() -> None:
    shared_affiliation = (
        "Cancer Center, Example University, shared.contact@example.edu"
    )
    first_author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=[shared_affiliation],
    )
    last_author = make_author(
        full_name="Alice Chen",
        position=2,
        is_last_author=True,
        affiliations=[shared_affiliation],
    )
    paper = make_paper([first_author, last_author])

    evidence = extract_email_evidence_from_paper(paper)

    assert len(evidence) == 2
    assert {item.matched_author_name for item in evidence} == {
        "John Smith",
        "Alice Chen",
    }
    assert {item.name_email_match_confidence for item in evidence} == {"medium"}
    assert {item.email for item in evidence} == {"shared.contact@example.edu"}


def test_extract_email_evidence_returns_missing_when_no_affiliation_email_exists() -> None:
    author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=["Department of Biology, Example University"],
    )
    paper = make_paper([author])

    evidence = extract_email_evidence_from_paper(paper)

    assert len(evidence) == 1
    item = evidence[0]
    assert item.email is None
    assert item.email_status == "missing"
    assert item.email_source_type == "pubmed_affiliation"
    assert item.email_source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert item.matched_author_name is None
    assert item.matched_affiliation is None
    assert item.name_email_match_confidence == "missing"
    assert item.email_reason == "source_data_not_provided"


def test_extract_email_evidence_marks_invalid_email_format() -> None:
    author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=["Department of Biology, contact john@example"],
    )
    paper = make_paper([author])

    evidence = extract_email_evidence_from_paper(paper)

    assert len(evidence) == 1
    item = evidence[0]
    assert item.email == "john@example"
    assert item.email_status == "invalid_format"
    assert item.matched_author_name == "John Smith"
    assert item.name_email_match_confidence == "invalid_format"
    assert item.email_reason == "invalid_email_format"


def test_extract_email_evidence_without_authors_requires_review() -> None:
    paper = make_paper(
        [],
        affiliations=["Example University, correspondence: info@example.edu"],
    )

    evidence = extract_email_evidence_from_paper(paper)

    assert len(evidence) == 1
    assert evidence[0].email == "info@example.edu"
    assert evidence[0].email_status == "needs_review"
    assert evidence[0].matched_author_name is None
    assert evidence[0].name_email_match_confidence == "needs_review"


def test_build_leads_from_paper_uses_high_confidence_email_author() -> None:
    author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=[
            "Department of Biology, Example University, john.smith@example.edu"
        ],
    )
    paper = make_paper([author])

    leads = build_leads_from_paper(paper)

    assert len(leads) == 1
    lead = leads[0]
    assert lead.lead_id == "pubmed-12345678-john-smith-example-edu"
    assert lead.pi_full_name == "John Smith"
    assert lead.verified_email == "john.smith@example.edu"
    assert lead.email_status == "verified_from_pubmed_affiliation"
    assert lead.email_source_url == "https://pubmed.ncbi.nlm.nih.gov/12345678/"
    assert lead.email_source_type == "pubmed_affiliation"
    assert lead.name_email_match_confidence == "high"
    assert lead.institution == (
        "Department of Biology, Example University, john.smith@example.edu"
    )
    assert lead.country == "unknown"
    assert lead.country_confidence == "pending"
    assert lead.recent_publication_title == "A title"
    assert lead.abstract == "An abstract"
    assert lead.journal == "A journal"
    assert lead.publication_year == 2024
    assert lead.pmid == "12345678"
    assert lead.doi == "10.1000/abc"
    assert lead.author_role == "email_author"
    assert lead.source_links == ["https://pubmed.ncbi.nlm.nih.gov/12345678/"]
    assert lead.data_quality == "email_evidence_available"
    assert lead.manual_review_required is False


def test_build_leads_from_paper_marks_medium_confidence_email_for_review() -> None:
    shared_affiliation = (
        "Cancer Center, Example University, shared.contact@example.edu"
    )
    first_author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=[shared_affiliation],
    )
    last_author = make_author(
        full_name="Alice Chen",
        position=2,
        is_last_author=True,
        affiliations=[shared_affiliation],
    )
    paper = make_paper([first_author, last_author])

    leads = build_leads_from_paper(paper)

    assert len(leads) == 2
    assert {lead.pi_full_name for lead in leads} == {"John Smith", "Alice Chen"}
    assert {lead.name_email_match_confidence for lead in leads} == {"medium"}
    assert {lead.data_quality for lead in leads} == {"email_evidence_needs_review"}
    assert all(lead.manual_review_required for lead in leads)
    assert all(lead.author_role == "email_author" for lead in leads)


def test_build_leads_from_paper_uses_last_author_when_no_email_exists() -> None:
    first_author = make_author(
        full_name="John Smith",
        position=1,
        affiliations=["Department of Biology, Example University"],
    )
    last_author = make_author(
        full_name="Alice Chen",
        position=2,
        is_last_author=True,
        affiliations=["Genome Center, Example Institute"],
    )
    paper = make_paper([first_author, last_author])

    leads = build_leads_from_paper(paper)

    assert len(leads) == 1
    lead = leads[0]
    assert lead.pi_full_name == "Alice Chen"
    assert lead.verified_email is None
    assert lead.email_status == "missing"
    assert lead.name_email_match_confidence == "missing"
    assert lead.institution == "Genome Center, Example Institute"
    assert lead.author_role == "candidate_pi_last_author"
    assert lead.data_quality == "missing_email_candidate"
    assert lead.manual_review_required is True
    assert "not confirmed PI" in lead.notes


def test_build_leads_from_paper_returns_empty_when_no_author_and_no_email() -> None:
    paper = make_paper([], affiliations=[])

    assert build_leads_from_paper(paper) == []


def test_build_leads_from_papers_combines_multiple_papers() -> None:
    first = make_paper(
        [
            make_author(
                full_name="John Smith",
                position=1,
                affiliations=["Example University, john.smith@example.edu"],
            )
        ]
    )
    second = make_paper(
        [
            make_author(
                full_name="Alice Chen",
                position=1,
                is_last_author=True,
                affiliations=["Example Institute"],
            )
        ]
    )

    leads = build_leads_from_papers([first, second])

    assert [lead.pi_full_name for lead in leads] == ["John Smith", "Alice Chen"]


def make_lead(
    *,
    name: str = "John Smith",
    email: str | None = "john.smith@example.edu",
    email_status: str = "verified_from_pubmed_affiliation",
    institution: str | None = "Example University",
    pmid: str = "12345678",
    source_links: list[str] | None = None,
) -> PubMedLead:
    return PubMedLead(
        lead_id=f"lead-{pmid}-{name}",
        pi_full_name=name,
        verified_email=email,
        email_status=email_status,
        email_source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if email else "missing",
        institution=institution,
        country="unknown",
        country_confidence="pending",
        recent_publication_title="A title",
        abstract="An abstract",
        journal="A journal",
        publication_year=2024,
        pmid=pmid,
        doi="10.1000/abc",
        author_role="email_author" if email else "candidate_pi_last_author",
        source_links=source_links or [f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"],
        data_quality="email_evidence_available" if email else "missing_email_candidate",
        manual_review_required=False if email else True,
        notes="Test lead.",
    )


def test_get_pubmed_lead_strong_dedup_key_prefers_verified_email() -> None:
    lead = make_lead(email="John.Smith@Example.edu", pmid="123")

    assert get_pubmed_lead_strong_dedup_key(lead) == (
        "email",
        "john.smith@example.edu",
    )


def test_get_pubmed_lead_strong_dedup_key_uses_pmid_author_without_verified_email() -> None:
    lead = make_lead(email=None, email_status="missing", name="John Smith", pmid="123")

    assert get_pubmed_lead_strong_dedup_key(lead) == (
        "pmid_author",
        "123|john smith",
    )


def test_deduplicate_pubmed_leads_merges_same_verified_email() -> None:
    first = make_lead(
        name="John Smith",
        email="john.smith@example.edu",
        pmid="123",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/123/"],
    )
    duplicate = make_lead(
        name="J Smith",
        email="John.Smith@Example.edu",
        pmid="456",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/456/"],
    )

    result = deduplicate_pubmed_leads([first, duplicate])

    assert len(result) == 1
    assert result[0].pi_full_name == "John Smith"
    assert result[0].merge_status == "confirmed"
    assert result[0].merge_reason == "email_match"
    assert result[0].source_links == [
        "https://pubmed.ncbi.nlm.nih.gov/123/",
        "https://pubmed.ncbi.nlm.nih.gov/456/",
    ]


def test_deduplicate_pubmed_leads_merges_same_pmid_and_author_without_email() -> None:
    first = make_lead(email=None, email_status="missing", name="Alice Chen", pmid="123")
    duplicate = make_lead(
        email=None,
        email_status="missing",
        name="Alice Chen",
        pmid="123",
    )

    result = deduplicate_pubmed_leads([first, duplicate])

    assert len(result) == 1
    assert result[0].merge_status == "confirmed"
    assert result[0].merge_reason == "same_pmid_author"


def test_deduplicate_pubmed_leads_marks_same_name_and_institution_as_candidate() -> None:
    first = make_lead(email=None, email_status="missing", name="Alice Chen", pmid="123")
    second = make_lead(email=None, email_status="missing", name="Alice Chen", pmid="456")

    result = deduplicate_pubmed_leads([first, second])

    assert len(result) == 2
    assert {lead.merge_status for lead in result} == {"candidate"}
    assert {lead.merge_reason for lead in result} == {"same_name_institution"}
    assert all(lead.manual_review_required for lead in result)


def test_deduplicate_pubmed_leads_does_not_merge_same_name_different_institution() -> None:
    first = make_lead(
        email=None,
        email_status="missing",
        name="Alice Chen",
        institution="Example University",
        pmid="123",
    )
    second = make_lead(
        email=None,
        email_status="missing",
        name="Alice Chen",
        institution="Different Institute",
        pmid="456",
    )

    result = deduplicate_pubmed_leads([first, second])

    assert len(result) == 2
    assert [lead.merge_status for lead in result] == ["not_merged", "not_merged"]
    assert [lead.merge_reason for lead in result] == [None, None]


def test_identify_affiliation_country_us_from_text() -> None:
    raw_affiliation = (
        "Department of Biology, Example University, Boston, MA, U.S.A."
    )

    result = parse_affiliation(raw_affiliation)

    assert result.institution == "Example University"
    assert result.country == "United States"
    assert result.country_confidence == "high"
    assert result.country_source == "affiliation_text"
    assert result.raw_affiliation == raw_affiliation


def test_identify_affiliation_country_uk_from_text() -> None:
    result = parse_affiliation(
        "School of Biology, University of Cambridge, Cambridge, England"
    )

    assert result.institution == "University of Cambridge"
    assert result.country == "United Kingdom"
    assert result.country_confidence == "high"
    assert result.country_source == "affiliation_text"


def test_identify_affiliation_country_china_from_text() -> None:
    result = parse_affiliation(
        "Genome Center, Example Institute, Shanghai, PR China"
    )

    assert result.institution == "Example Institute"
    assert result.country == "China"
    assert result.country_confidence == "high"
    assert result.country_source == "affiliation_text"


def test_identify_affiliation_country_japan_from_text() -> None:
    result = parse_affiliation(
        "Department of Genomics, Kyoto University, Kyoto, Japan"
    )

    assert result.institution == "Kyoto University"
    assert result.country == "Japan"
    assert result.country_confidence == "high"
    assert result.country_source == "affiliation_text"


def test_identify_affiliation_unknown_country_when_text_has_no_country() -> None:
    country = identify_country_from_affiliation(
        "Department of Biology, Example University"
    )

    assert country.country == "unknown"
    assert country.country_confidence == "unknown"
    assert country.country_source == "unknown"


def test_identify_affiliation_handles_empty_affiliation() -> None:
    result = parse_affiliation("")

    assert result.institution is None
    assert result.country == "unknown"
    assert result.country_confidence == "unknown"
    assert result.country_source == "unknown"
    assert result.raw_affiliation is None


def test_identify_institution_keeps_basic_candidate_when_country_is_unknown() -> None:
    institution = identify_institution_from_affiliation(
        "Department of Biology, Example University"
    )

    assert institution == "Example University"


def test_email_domain_is_auxiliary_country_evidence_only() -> None:
    country = identify_country_from_affiliation(
        "Department of Biology, Example University",
        email="alice@cam.ac.uk",
    )

    assert country.country == "United Kingdom"
    assert country.country_confidence == "medium"
    assert country.country_source == "email_domain_auxiliary"


def test_enrich_lead_affiliation_preserves_raw_affiliation_and_fills_fields() -> None:
    raw_affiliation = (
        "Department of Biology, Example University, Boston, MA, USA"
    )
    lead = make_lead(
        email="john.smith@example.edu",
        institution=raw_affiliation,
    )

    enriched = enrich_lead_affiliation(lead)

    assert enriched.institution == "Example University"
    assert enriched.country == "United States"
    assert enriched.country_confidence == "high"
    assert enriched.country_source == "affiliation_text"
    assert enriched.raw_affiliation == raw_affiliation
