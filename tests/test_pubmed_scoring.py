from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper
from scholarlead_agent.pubmed_scoring import (
    assign_priority,
    calculate_pubmed_lead_score,
    enrich_lead_keyword_match,
    enrich_leads_keyword_match,
    extract_query_terms,
    find_matched_keywords,
    match_pubmed_paper_keywords,
    normalize_keywords,
    score_email_contactability,
    score_publication_recency,
    score_pubmed_lead,
    score_pubmed_leads,
)


def make_paper(
    *,
    title: str = "A title",
    abstract: str = "An abstract",
    mesh_terms: list[str] | None = None,
    keywords: list[str] | None = None,
    pmid: str = "12345678",
) -> PubMedPaper:
    return PubMedPaper(
        source="pubmed",
        pmid=pmid,
        doi="10.1000/abc",
        title=title,
        abstract=abstract,
        journal="A journal",
        publication_date="2024-01-01",
        publication_year=2024,
        article_types=[],
        mesh_terms=mesh_terms or [],
        keywords=keywords or [],
        authors=[],
        affiliations=[],
        source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    )


def make_lead(
    *,
    title: str = "A title",
    abstract: str = "An abstract",
    pmid: str = "12345678",
    email: str | None = "john.smith@example.edu",
    email_status: str = "verified_from_pubmed_affiliation",
    publication_year: int | None = 2024,
    topic_match_score: int = 0,
    matched_keywords: list[str] | None = None,
) -> PubMedLead:
    return PubMedLead(
        lead_id=f"lead-{pmid}",
        pi_full_name="John Smith",
        verified_email=email,
        email_status=email_status,
        email_source_url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high" if email else "missing",
        institution="Example University",
        country="unknown",
        country_confidence="pending",
        recent_publication_title=title,
        abstract=abstract,
        journal="A journal",
        publication_year=publication_year,
        pmid=pmid,
        doi="10.1000/abc",
        author_role="email_author" if email else "candidate_pi_last_author",
        source_links=[f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"],
        data_quality="email_evidence_available" if email else "missing_email_candidate",
        manual_review_required=False if email else True,
        notes="Test lead.",
        matched_keywords=matched_keywords or [],
        topic_match_score=topic_match_score,
    )


def test_normalize_keywords_splits_and_deduplicates() -> None:
    assert normalize_keywords("RNA-seq, Spatial Transcriptomics; rna-seq") == [
        "rna-seq",
        "spatial transcriptomics",
    ]


def test_extract_query_terms_prefers_phrase_then_tokens() -> None:
    terms = extract_query_terms("single cell RNA sequencing")

    assert terms[:1] == ["single cell rna sequencing"]
    assert "single" in terms
    assert "cell" in terms
    assert "rna" in terms
    assert "sequencing" in terms


def test_find_matched_keywords_from_title() -> None:
    matched = find_matched_keywords(
        query="spatial transcriptomics",
        title="Spatial transcriptomics reveals tumor regions",
    )

    assert matched == ["spatial transcriptomics"]


def test_find_matched_keywords_from_abstract() -> None:
    matched = find_matched_keywords(
        query="single cell",
        abstract="This study uses single cell profiling in cancer samples.",
    )

    assert matched == ["single cell"]


def test_find_matched_keywords_from_mesh_terms() -> None:
    matched = find_matched_keywords(
        query="genomics",
        mesh_terms=["Genomics", "Neoplasms"],
    )

    assert matched == ["genomics"]


def test_find_matched_keywords_from_keywords() -> None:
    matched = find_matched_keywords(
        query="rna-seq",
        keywords=["RNA-seq", "Transcriptome"],
    )

    assert matched == ["rna-seq"]


def test_match_pubmed_paper_keywords_writes_service_type_and_reason() -> None:
    paper = make_paper(
        title="Single cell analysis of immune cells",
        mesh_terms=["Single Cell Analysis"],
    )

    result = match_pubmed_paper_keywords(
        paper,
        query="single cell",
        service_type="transcriptome sequencing",
    )

    assert result.matched_keywords == ["single cell"]
    assert result.target_service_type == "transcriptome sequencing"
    assert result.topic_match_score == 60
    assert "Matched keywords: single cell" in result.topic_match_reason
    assert "Target service type: transcriptome sequencing" in result.topic_match_reason
    assert "default rule / pending client keyword hierarchy" in result.topic_match_reason


def test_match_pubmed_paper_keywords_returns_no_match_without_guessing() -> None:
    paper = make_paper(title="Protein structure study", abstract="")

    result = match_pubmed_paper_keywords(
        paper,
        query="single cell",
        service_type=None,
    )

    assert result.matched_keywords == []
    assert result.target_service_type is None
    assert result.topic_match_score == 0
    assert result.topic_match_reason == (
        "No matched keywords. default rule / pending client keyword hierarchy."
    )


def test_keyword_matching_is_case_insensitive() -> None:
    matched = find_matched_keywords(
        query="SPATIAL TRANSCRIPTOMICS",
        title="spatial transcriptomics in plants",
    )

    assert matched == ["spatial transcriptomics"]


def test_keyword_matching_handles_empty_abstract_and_keywords() -> None:
    result = match_pubmed_paper_keywords(
        make_paper(title="", abstract="", mesh_terms=[], keywords=[]),
        query="genomics",
    )

    assert result.matched_keywords == []
    assert result.topic_match_score == 0


def test_enrich_lead_keyword_match_fills_stage11_fields() -> None:
    lead = make_lead(
        title="Spatial transcriptomics in tumor samples",
        abstract="No extra terms.",
    )

    enriched = enrich_lead_keyword_match(
        lead,
        query="spatial transcriptomics",
        service_type="spatial omics",
    )

    assert enriched.matched_keywords == ["spatial transcriptomics"]
    assert enriched.target_service_type == "spatial omics"
    assert enriched.topic_match_score == 60
    assert "Matched keywords: spatial transcriptomics" in enriched.topic_match_reason


def test_enrich_leads_keyword_match_can_use_paper_mesh_and_keywords() -> None:
    lead = make_lead(title="", abstract="", pmid="123")
    paper = make_paper(mesh_terms=["Genomics"], keywords=["RNA-seq"], pmid="123")

    enriched = enrich_leads_keyword_match(
        [lead],
        query="genomics",
        service_type="sequencing",
        paper_by_pmid={"123": paper},
    )

    assert len(enriched) == 1
    assert enriched[0].matched_keywords == ["genomics"]
    assert enriched[0].target_service_type == "sequencing"


def test_score_publication_recency_uses_stable_year_buckets() -> None:
    assert score_publication_recency(2026, reference_year=2026) == 100
    assert score_publication_recency(2024, reference_year=2026) == 100
    assert score_publication_recency(2021, reference_year=2026) == 70
    assert score_publication_recency(2016, reference_year=2026) == 40
    assert score_publication_recency(2015, reference_year=2026) == 0
    assert score_publication_recency(None, reference_year=2026) == 0


def test_score_email_contactability_from_email_evidence_only() -> None:
    assert (
        score_email_contactability(
            email_status="verified_from_pubmed_affiliation",
            verified_email="john.smith@example.edu",
        )
        == 100
    )
    assert (
        score_email_contactability(
            email_status="needs_review",
            verified_email="shared@example.edu",
        )
        == 60
    )
    assert (
        score_email_contactability(
            email_status="missing",
            verified_email=None,
        )
        == 0
    )


def test_calculate_pubmed_lead_score_uses_fixed_weights() -> None:
    assert (
        calculate_pubmed_lead_score(
            topic_match_score=80,
            publication_recency_score=70,
            email_contactability_score=60,
        )
        == 73
    )


def test_assign_priority_boundaries() -> None:
    assert assign_priority(80) == "high"
    assert assign_priority(79) == "medium"
    assert assign_priority(50) == "medium"
    assert assign_priority(49) == "low"


def test_score_pubmed_lead_high_match_recent_verified_email_is_high_priority() -> None:
    lead = make_lead(
        publication_year=2026,
        topic_match_score=100,
        matched_keywords=["single cell", "rna-seq"],
    )

    scored = score_pubmed_lead(lead, reference_year=2026)

    assert scored.topic_match_score == 100
    assert scored.publication_recency_score == 100
    assert scored.email_contactability_score == 100
    assert scored.lead_score == 100
    assert scored.priority == "high"
    assert "topic_match_score=100 weighted 50%" in scored.score_explanation
    assert "lead_score=100" in scored.score_explanation


def test_score_pubmed_lead_weak_match_old_missing_email_is_low_priority() -> None:
    lead = make_lead(
        email=None,
        email_status="missing",
        publication_year=2010,
        topic_match_score=0,
        matched_keywords=[],
    )

    scored = score_pubmed_lead(lead, reference_year=2026)

    assert scored.publication_recency_score == 0
    assert scored.email_contactability_score == 0
    assert scored.lead_score == 0
    assert scored.priority == "low"


def test_score_pubmed_lead_80_boundary_is_high_priority() -> None:
    lead = make_lead(
        email=None,
        email_status="missing",
        publication_year=2026,
        topic_match_score=100,
    )

    scored = score_pubmed_lead(lead, reference_year=2026)

    assert scored.lead_score == 80
    assert scored.priority == "high"


def test_score_pubmed_lead_50_boundary_is_medium_priority() -> None:
    lead = make_lead(
        email=None,
        email_status="missing",
        publication_year=2010,
        topic_match_score=100,
    )

    scored = score_pubmed_lead(lead, reference_year=2026)

    assert scored.lead_score == 50
    assert scored.priority == "medium"


def test_score_pubmed_lead_keeps_funding_and_outsourcing_as_unscored_placeholders() -> None:
    scored = score_pubmed_lead(make_lead(topic_match_score=60), reference_year=2026)

    assert scored.funding_activity_score is None
    assert scored.funding_activity_reason == (
        "Funding source not connected in PubMed-only first round"
    )
    assert scored.outsourcing_tendency_score is None
    assert scored.official_scoring_status == "pending_multi_source_data"
    assert "not scored because multi-source data is not connected" in (
        scored.score_explanation
    )


def test_score_pubmed_leads_scores_multiple_leads() -> None:
    leads = [
        make_lead(pmid="1", publication_year=2026, topic_match_score=100),
        make_lead(
            pmid="2",
            email=None,
            email_status="missing",
            publication_year=2010,
            topic_match_score=0,
        ),
    ]

    scored = score_pubmed_leads(leads, reference_year=2026)

    assert [lead.lead_score for lead in scored] == [100, 0]
    assert [lead.priority for lead in scored] == ["high", "low"]
