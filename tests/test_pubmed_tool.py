from pathlib import Path

from scholarlead_agent.pubmed_models import PubMedAuthor, PubMedLead, PubMedPaper, PubMedSearchParams
from scholarlead_agent.pubmed_storage import PubMedProcessedOutputPaths, PubMedRawOutputPaths
from scholarlead_agent.services.pubmed_service import PubMedRunResult
from scholarlead_agent.tools.pubmed_tool import (
    SEARCH_PUBMED_INPUT_SCHEMA,
    SEARCH_PUBMED_TOOL,
    search_pubmed,
)


def make_paper() -> PubMedPaper:
    author = PubMedAuthor(
        full_name="Lei S Qi",
        last_name="Qi",
        fore_name="Lei S",
        initials="LS",
        author_position=3,
        is_last_author=True,
        affiliations=["Stanford University, Stanford, CA, USA. slqi@stanford.edu."],
    )
    return PubMedPaper(
        source="pubmed",
        pmid="41951915",
        doi="10.1038/example",
        title="CRISPR-Cas-based live cell imaging of genome dynamics.",
        abstract="Abstract text.",
        journal="Nature Methods",
        publication_date="2026-04-06",
        publication_year=2026,
        article_types=["Journal Article"],
        mesh_terms=[],
        keywords=["CRISPR"],
        authors=[author],
        affiliations=author.affiliations,
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        raw_record_path="data/raw/pubmed/example_efetch.xml",
    )


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="pubmed-41951915-lei-s-qi-stanford-edu",
        pi_full_name="Lei S Qi",
        verified_email="slqi@stanford.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Stanford University",
        country="United States",
        country_confidence="high",
        recent_publication_title="CRISPR-Cas-based live cell imaging of genome dynamics.",
        abstract="Abstract text.",
        journal="Nature Methods",
        publication_year=2026,
        pmid="41951915",
        doi="10.1038/example",
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/41951915/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Email found in PubMed affiliation.",
        country_source="affiliation_text",
        raw_affiliation="Stanford University, Stanford, CA, USA. slqi@stanford.edu.",
        matched_keywords=["crispr"],
        target_service_type="genome imaging",
        topic_match_score=80,
        publication_recency_score=100,
        email_contactability_score=100,
        lead_score=90,
        priority="high",
        score_explanation="PubMed-only temporary score.",
    )


def make_result(
    *,
    status: str = "success",
    errors: list[dict[str, str]] | None = None,
) -> PubMedRunResult:
    params = PubMedSearchParams(
        query="Cas-based genome",
        from_date="2026-04-05",
        to_date="2026-04-10",
        max_results=5,
        service_type="genome imaging",
    )
    raw_paths = PubMedRawOutputPaths(
        esearch_json=Path("data/raw/pubmed/example_esearch.json"),
        efetch_xml=Path("data/raw/pubmed/example_efetch.xml"),
        request_meta_json=Path("data/raw/pubmed/example_request_meta.json"),
    )
    processed_paths = PubMedProcessedOutputPaths(
        papers_json=Path("data/processed/pubmed/papers.json"),
        papers_csv=Path("data/processed/pubmed/papers.csv"),
        leads_json=Path("data/processed/pubmed/leads.json"),
        leads_csv=Path("data/processed/pubmed/leads.csv"),
    )
    paper = make_paper()
    lead = make_lead()
    return PubMedRunResult(
        task_id="pubmed-tool-test",
        status=status,
        search_params=params,
        pmids=["41951915"] if status == "success" else [],
        papers=[paper] if status == "success" else [],
        leads=[lead] if status == "success" else [],
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        raw_files={"esearch_json": str(raw_paths.esearch_json)},
        processed_files={"leads_csv": str(processed_paths.leads_csv)}
        if status == "success"
        else {},
        run_report_path=Path("data/processed/pubmed/run_report.json"),
        run_report={"scoring_mode": "pubmed_single_source_temporary"},
        errors=errors or [],
        started_at="2026-08-20T12:00:00",
        finished_at="2026-08-20T12:00:01",
    )


def valid_arguments() -> dict[str, object]:
    return {
        "query": "Cas-based genome",
        "from_date": "2026-04-05",
        "to_date": "2026-04-10",
        "max_results": 5,
        "service_type": "genome imaging",
    }


def test_search_pubmed_tool_definition_is_clear_and_external() -> None:
    assert SEARCH_PUBMED_TOOL.name == "search_pubmed"
    assert SEARCH_PUBMED_TOOL.effect == "external"
    assert SEARCH_PUBMED_TOOL.handler is search_pubmed
    assert "real PubMed records" in SEARCH_PUBMED_TOOL.description
    assert "must not be used to send email" in SEARCH_PUBMED_TOOL.description


def test_search_pubmed_input_schema_matches_pubmed_limits() -> None:
    assert SEARCH_PUBMED_INPUT_SCHEMA["required"] == [
        "query",
        "from_date",
        "to_date",
        "max_results",
    ]
    assert SEARCH_PUBMED_INPUT_SCHEMA["properties"]["max_results"]["minimum"] == 1
    assert SEARCH_PUBMED_INPUT_SCHEMA["properties"]["max_results"]["maximum"] == 100
    assert SEARCH_PUBMED_INPUT_SCHEMA["additionalProperties"] is False


def test_search_pubmed_success_calls_service_and_returns_evidence() -> None:
    calls: list[PubMedSearchParams] = []

    def fake_service(params: PubMedSearchParams) -> PubMedRunResult:
        calls.append(params)
        return make_result()

    result = search_pubmed(valid_arguments(), service_runner=fake_service)

    assert result.success is True
    assert result.source == "pubmed"
    assert result.error_code is None
    assert len(calls) == 1
    assert calls[0].query == "Cas-based genome"
    assert result.data["task_id"] == "pubmed-tool-test"
    assert result.data["paper_count"] == 1
    assert result.data["lead_count"] == 1
    assert result.data["papers"][0]["pmid"] == "41951915"
    assert result.data["papers"][0]["source_url"] == (
        "https://pubmed.ncbi.nlm.nih.gov/41951915/"
    )
    assert result.data["leads"][0]["pi_full_name"] == "Lei S Qi"
    assert result.data["leads"][0]["verified_email"] == "slqi@stanford.edu"
    assert result.data["leads"][0]["email_source_url"] == (
        "https://pubmed.ncbi.nlm.nih.gov/41951915/"
    )
    assert result.data["leads"][0]["lead_score"] == 90
    assert result.data["run_report_path"].endswith("run_report.json")


def test_search_pubmed_rejects_empty_query_before_service_call() -> None:
    calls = 0

    def fake_service(params: PubMedSearchParams) -> PubMedRunResult:
        nonlocal calls
        calls += 1
        return make_result()

    arguments = valid_arguments()
    arguments["query"] = " "

    result = search_pubmed(arguments, service_runner=fake_service)

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "query cannot be empty" in (result.error_message or "")
    assert calls == 0


def test_search_pubmed_rejects_invalid_date_before_service_call() -> None:
    result = search_pubmed(
        {
            "query": "genome",
            "from_date": "2026/04/05",
            "to_date": "2026-04-10",
            "max_results": 5,
        },
        service_runner=lambda params: make_result(),
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "from_date must be in YYYY-MM-DD format" in (result.error_message or "")


def test_search_pubmed_rejects_max_results_outside_limit() -> None:
    for value in [0, 101]:
        arguments = valid_arguments()
        arguments["max_results"] = value

        result = search_pubmed(arguments, service_runner=lambda params: make_result())

        assert result.success is False
        assert result.error_code == "invalid_arguments"
        assert "max_results must be between 1 and 100" in (result.error_message or "")


def test_search_pubmed_converts_service_stage_errors() -> None:
    def fake_service(params: PubMedSearchParams) -> PubMedRunResult:
        return make_result(
            status="partial_failure",
            errors=[
                {
                    "stage": "efetch",
                    "type": "RuntimeError",
                    "message": "EFetch failed",
                }
            ],
        )

    result = search_pubmed(valid_arguments(), service_runner=fake_service)

    assert result.success is False
    assert result.error_code == "pubmed_fetch_failed"
    assert result.error_message == "EFetch failed"
    assert result.data["status"] == "partial_failure"
    assert result.errors[0]["stage"] == "efetch"


def test_search_pubmed_converts_unexpected_service_exception() -> None:
    def fake_service(params: PubMedSearchParams) -> PubMedRunResult:
        raise RuntimeError("boom")

    result = search_pubmed(valid_arguments(), service_runner=fake_service)

    assert result.success is False
    assert result.error_code == "tool_execution_error"
    assert result.error_message == "boom"
