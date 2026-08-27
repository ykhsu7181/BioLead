from pathlib import Path

from scholarlead_agent.services.openalex_service import OpenAlexRunResult
from scholarlead_agent.storage import OutputPaths
from scholarlead_agent.tools.openalex_tool import SEARCH_OPENALEX_TOOL, search_openalex
from scholarlead_agent.unified_converters import openalex_record_to_unified_paper
from scholarlead_agent.works import PaperRecord, SearchParams


def make_result(params: SearchParams, *, status: str = "success") -> OpenAlexRunResult:
    work = PaperRecord(
        openalex_id="https://openalex.org/W1",
        doi="10.1000/abc",
        title="Single-cell cancer atlas",
        abstract="Single-cell atlas",
        publication_date="2025-03-04",
        authors=["Alice Smith"],
        institutions=["Example University"],
    )
    output_paths = OutputPaths(
        raw_json=Path("data/raw/openalex/raw.json"),
        processed_json=Path("data/processed/openalex/processed.json"),
        processed_csv=Path("data/processed/openalex/processed.csv"),
        request_meta_json=Path("data/raw/openalex/request_meta.json"),
    )
    errors = [] if status == "success" else [
        {"stage": "fetch", "type": "RuntimeError", "message": "OpenAlex failed"}
    ]
    return OpenAlexRunResult(
        task_id="openalex-tool-test",
        status=status,
        search_params=params,
        works=[work] if status == "success" else [],
        unified_papers=[openalex_record_to_unified_paper(work)]
        if status == "success"
        else [],
        output_paths=output_paths,
        raw_files={"raw_json": str(output_paths.raw_json)},
        processed_files={"processed_json": str(output_paths.processed_json)}
        if status == "success"
        else {},
        run_report_path=Path("data/processed/openalex/run_report.json"),
        run_report={},
        errors=errors,
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )


def test_search_openalex_tool_returns_structured_result() -> None:
    calls: list[SearchParams] = []

    def fake_runner(params: SearchParams) -> OpenAlexRunResult:
        calls.append(params)
        return make_result(params)

    result = search_openalex(
        {
            "query": "single-cell cancer",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
            "max_results": 5,
        },
        service_runner=fake_runner,
    )

    assert result.success is True
    assert result.source == "openalex"
    assert calls[0].query == "single-cell cancer"
    assert result.data["work_count"] == 1
    assert result.data["works"][0]["openalex_id"] == "https://openalex.org/W1"
    assert result.data["unified_paper_count"] == 1
    assert result.data["unified_papers"][0]["source_name"] == "openalex"
    assert result.data["lead_generation_status"] == "not_enabled_in_stage21c"
    assert result.data["scoring_status"] == "not_enabled_in_stage21c"
    assert result.data["email_status"] == "not_enabled_in_stage21c"


def test_search_openalex_tool_rejects_invalid_date() -> None:
    result = search_openalex(
        {
            "query": "single-cell cancer",
            "from_date": "2025/01/01",
            "to_date": "2025-12-31",
            "max_results": 5,
        },
        service_runner=lambda params: make_result(params),
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "from_date must use YYYY-MM-DD format" in (result.error_message or "")


def test_search_openalex_tool_converts_failed_run_result() -> None:
    def failed_runner(params: SearchParams) -> OpenAlexRunResult:
        return make_result(params, status="failed")

    result = search_openalex(
        {
            "query": "single-cell cancer",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31",
            "max_results": 5,
        },
        service_runner=failed_runner,
    )

    assert result.success is False
    assert result.error_code == "openalex_fetch_failed"
    assert result.errors[0]["stage"] == "fetch"


def test_openalex_tool_schema_has_no_send_or_scoring_action() -> None:
    serialized = str(SEARCH_OPENALEX_TOOL)

    assert SEARCH_OPENALEX_TOOL.name == "search_openalex"
    assert SEARCH_OPENALEX_TOOL.effect == "external"
    assert "send_email" not in serialized
    assert "score_lead" not in serialized
