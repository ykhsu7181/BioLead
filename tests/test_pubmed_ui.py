from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedLead, PubMedPaper
from scholarlead_agent.ui.streamlit_app import (
    build_summary_metrics,
    filter_lead_rows,
    get_filter_options,
    leads_to_table_rows,
    papers_to_table_rows,
)


def make_paper() -> PubMedPaper:
    author = PubMedAuthor(
        full_name="Alice Smith",
        last_name="Smith",
        fore_name="Alice",
        initials="AS",
        author_position=1,
        is_last_author=True,
        affiliations=["Example University, Boston, MA, USA"],
    )
    return PubMedPaper(
        source="pubmed",
        pmid="12345678",
        doi="10.1000/example",
        title="Single cell RNA sequencing in cancer",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_date="2024-01-01",
        publication_year=2024,
        article_types=["Journal Article"],
        mesh_terms=["Neoplasms"],
        keywords=["single cell"],
        authors=[author],
        affiliations=author.affiliations,
        source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
    )


def make_lead(
    *,
    lead_id: str,
    country: str,
    priority: str,
    email_status: str,
) -> PubMedLead:
    verified_email = (
        "alice.smith@example.edu"
        if email_status == "verified_from_pubmed_affiliation"
        else None
    )
    return PubMedLead(
        lead_id=lead_id,
        pi_full_name="Alice Smith",
        verified_email=verified_email,
        email_status=email_status,
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/12345678/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if verified_email else "missing",
        institution="Example University",
        country=country,
        country_confidence="high" if country != "unknown" else "unknown",
        recent_publication_title="Single cell RNA sequencing in cancer",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_year=2024,
        pmid="12345678",
        doi="10.1000/example",
        author_role="email_author" if verified_email else "candidate_pi_last_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/12345678/"],
        data_quality="email_evidence_available" if verified_email else "missing_email_candidate",
        manual_review_required=not bool(verified_email),
        notes="Test lead.",
        country_source="affiliation_text" if country != "unknown" else "unknown",
        raw_affiliation="Example University, Boston, MA, USA",
        matched_keywords=["single cell"],
        target_service_type="scRNA-seq",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100 if verified_email else 0,
        lead_score=90 if priority == "high" else 40,
        priority=priority,
        score_explanation="PubMed-only temporary score.",
    )


def test_build_summary_metrics_orders_core_counts() -> None:
    metrics = build_summary_metrics(
        {
            "status": "success",
            "pmid_count": 2,
            "paper_count": 2,
            "lead_count": 1,
            "leads_with_verified_email_count": 1,
            "missing_email_count": 0,
            "started_at": "2026-08-19T10:00:00",
            "finished_at": "2026-08-19T10:00:01",
        }
    )

    assert metrics[:6] == [
        ("Status", "success"),
        ("PMIDs", 2),
        ("Papers", 2),
        ("Leads", 1),
        ("Verified email leads", 1),
        ("Missing email", 0),
    ]


def test_papers_to_table_rows_contains_required_display_fields() -> None:
    rows = papers_to_table_rows([make_paper()])

    assert rows == [
        {
            "PMID": "12345678",
            "Title": "Single cell RNA sequencing in cancer",
            "Journal": "Example Journal",
            "Publication Year": 2024,
            "DOI": "10.1000/example",
            "Authors": "Alice Smith",
            "Source URL": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
        }
    ]


def test_leads_to_table_rows_and_filters_support_stage18_view() -> None:
    rows = leads_to_table_rows(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            ),
            make_lead(
                lead_id="lead-2",
                country="unknown",
                priority="low",
                email_status="missing",
            ),
        ]
    )

    assert rows[0]["PI / Candidate"] == "Alice Smith"
    assert rows[0]["Verified Email"] == "alice.smith@example.edu"
    assert rows[1]["Verified Email"] == "missing"
    assert get_filter_options(rows, "Priority") == ["All", "high", "low"]

    filtered = filter_lead_rows(
        rows,
        country="United States",
        priority="high",
        email_status="verified_from_pubmed_affiliation",
    )

    assert len(filtered) == 1
    assert filtered[0]["Lead ID"] == "lead-1"


def test_filter_lead_rows_all_keeps_rows() -> None:
    rows = leads_to_table_rows(
        [
            make_lead(
                lead_id="lead-1",
                country="United States",
                priority="high",
                email_status="verified_from_pubmed_affiliation",
            )
        ]
    )

    assert filter_lead_rows(
        rows,
        country="All",
        priority="All",
        email_status="All",
    ) == rows
