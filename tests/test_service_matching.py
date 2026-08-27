from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.service_catalog import CompanyService, CompanyServiceCatalog
from scholarlead_agent.service_matching import (
    SERVICE_MATCHER_VERSION,
    ServiceMatchInput,
    match_company_service,
    service_match_input_from_lead,
    service_match_result_to_dict,
)


def make_catalog() -> CompanyServiceCatalog:
    return CompanyServiceCatalog(
        catalog_version="2026-08-26-v1",
        source_path="test.csv",
        services=[
            CompanyService(
                catalog_version="2026-08-26-v1",
                updated_at="2026-08-26",
                service_id="single_cell_rna_seq",
                service_name="Single-cell RNA sequencing",
                service_category="sequencing",
                description="Single-cell services",
                positive_keywords=["single-cell", "cancer", "immune"],
                negative_keywords=["spatial transcriptomics"],
                synonyms=["scRNA-seq"],
                application_fields=["tumor microenvironment"],
                supported_organisms=["human"],
                enabled=True,
            ),
            CompanyService(
                catalog_version="2026-08-26-v1",
                updated_at="2026-08-26",
                service_id="crispr_screening",
                service_name="CRISPR screening",
                service_category="functional genomics",
                description="CRISPR services",
                positive_keywords=["CRISPR", "screening"],
                synonyms=["gene editing"],
                enabled=True,
            ),
        ],
    )


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="lead-1",
        pi_full_name="Alice Smith",
        verified_email="alice@example.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Example University",
        country="United States",
        country_confidence="high",
        recent_publication_title="Single-cell RNA sequencing reveals cancer immune states",
        abstract="This study uses scRNA-seq to study human tumor microenvironment.",
        journal="Example Journal",
        publication_year=2026,
        pmid="1",
        doi=None,
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/1/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Test lead.",
        matched_keywords=["single-cell", "cancer"],
        target_service_type="single-cell RNA sequencing",
    )


def test_match_company_service_returns_best_service_with_versions() -> None:
    result = match_company_service(
        ServiceMatchInput(
            paper_title="Single-cell RNA sequencing in cancer",
            abstract="Human immune tumor microenvironment profiling with scRNA-seq.",
            keywords=["cancer"],
        ),
        make_catalog(),
    )

    assert result.status == "matched"
    assert result.service_id == "single_cell_rna_seq"
    assert result.match_score > 0
    assert "single-cell" in result.matched_terms
    assert result.catalog_version == "2026-08-26-v1"
    assert result.matcher_version == SERVICE_MATCHER_VERSION
    assert "matched term" in result.evidence[0]


def test_match_company_service_returns_no_match_without_creating_service() -> None:
    result = match_company_service(
        ServiceMatchInput(
            paper_title="A clinical case report",
            abstract="No relevant omics service terms are present.",
        ),
        make_catalog(),
    )

    assert result.status == "no_match"
    assert result.service_id is None
    assert result.service_name is None
    assert result.match_score == 0


def test_match_company_service_ignores_disabled_service() -> None:
    catalog = CompanyServiceCatalog(
        catalog_version="2026-08-26-v1",
        source_path="test.csv",
        services=[
            CompanyService(
                catalog_version="2026-08-26-v1",
                updated_at="2026-08-26",
                service_id="disabled_spatial",
                service_name="Disabled Spatial",
                service_category="spatial",
                description="Disabled service",
                positive_keywords=["spatial transcriptomics"],
                enabled=False,
            )
        ],
    )

    result = match_company_service(
        ServiceMatchInput(
            paper_title="Spatial transcriptomics of tumor microenvironment",
        ),
        catalog,
    )

    assert result.status == "disabled_service"
    assert result.service_id is None


def test_service_match_input_from_lead_uses_lead_evidence() -> None:
    match_input = service_match_input_from_lead(make_lead())

    assert match_input.paper_title.startswith("Single-cell")
    assert "scRNA-seq" in match_input.abstract
    assert match_input.matched_keywords == ["single-cell", "cancer"]
    assert match_input.research_direction == "single-cell RNA sequencing"


def test_service_match_result_to_dict_is_export_ready() -> None:
    result = match_company_service(
        ServiceMatchInput(paper_title="CRISPR screening for cancer targets"),
        make_catalog(),
    )

    data = service_match_result_to_dict(result)

    assert data["service_id"] == "crispr_screening"
    assert data["catalog_version"] == "2026-08-26-v1"
    assert data["matcher_version"] == SERVICE_MATCHER_VERSION
    assert isinstance(data["matched_terms"], list)
