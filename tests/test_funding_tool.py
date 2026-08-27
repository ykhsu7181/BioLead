from pathlib import Path

from scholarlead_agent.nih_reporter_models import NIHFundingRecord, NIHReporterSearchParams
from scholarlead_agent.services.nih_reporter_service import NIHReporterRunResult
from scholarlead_agent.tools.funding_tool import SEARCH_FUNDING_TOOL, search_funding
from scholarlead_agent.unified_converters import nih_funding_record_to_unified_funding


def make_result(
    params: NIHReporterSearchParams,
    *,
    status: str = "success",
) -> NIHReporterRunResult:
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
        raw_record_path="data/raw/nih_reporter/raw.json",
    )
    errors = [] if status == "success" else [
        {"stage": "search", "type": "RuntimeError", "message": "NIH failed"}
    ]
    return NIHReporterRunResult(
        task_id="nih-reporter-tool-test",
        status=status,
        search_params=params,
        funding_records=[record] if status == "success" else [],
        unified_funding=[nih_funding_record_to_unified_funding(record)]
        if status == "success"
        else [],
        raw_paths=None,  # type: ignore[arg-type]
        processed_paths=None,  # type: ignore[arg-type]
        raw_files={"projects_json": "data/raw/nih_reporter/raw.json"},
        processed_files={"funding_json": "data/processed/nih_reporter/funding.json"}
        if status == "success"
        else {},
        run_report_path=Path("data/processed/nih_reporter/run_report.json"),
        run_report={},
        errors=errors,
        started_at="2026-08-24T12:00:00",
        finished_at="2026-08-24T12:00:01",
    )


def test_search_funding_tool_returns_structured_result() -> None:
    calls: list[NIHReporterSearchParams] = []

    def fake_runner(params: NIHReporterSearchParams) -> NIHReporterRunResult:
        calls.append(params)
        return make_result(params)

    result = search_funding(
        {
            "pi_name": "Lei S Qi",
            "institution": "Stanford University",
            "keyword": "CRISPR imaging",
            "from_year": 2025,
            "to_year": 2026,
            "max_results": 5,
        },
        service_runner=fake_runner,
    )

    assert result.success is True
    assert result.source == "nih_reporter"
    assert calls[0].pi_name == "Lei S Qi"
    assert result.data["funding_count"] == 1
    assert result.data["funding_records"][0]["grant_id"] == "R01CA123456"
    assert result.data["unified_funding_count"] == 1
    assert result.data["unified_funding"][0]["agency"] == "NCI"
    assert result.data["coverage_note"].startswith("NIH RePORTER only covers")
    assert result.data["official_scoring_status"] == "not_enabled_in_stage21d"
    assert result.data["email_status"] == "not_enabled_in_stage21d"


def test_search_funding_tool_rejects_missing_search_text() -> None:
    result = search_funding(
        {
            "from_year": 2025,
            "to_year": 2026,
            "max_results": 5,
        },
        service_runner=lambda params: make_result(params),
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "pi_name, institution, or keyword is required" in (
        result.error_message or ""
    )


def test_search_funding_tool_converts_failed_run_result() -> None:
    def failed_runner(params: NIHReporterSearchParams) -> NIHReporterRunResult:
        return make_result(params, status="failed")

    result = search_funding(
        {
            "keyword": "cancer",
            "from_year": 2025,
            "to_year": 2026,
            "max_results": 5,
        },
        service_runner=failed_runner,
    )

    assert result.success is False
    assert result.error_code == "nih_reporter_search_failed"
    assert result.errors[0]["stage"] == "search"


def test_search_funding_tool_schema_has_no_send_or_scoring_action() -> None:
    serialized = str(SEARCH_FUNDING_TOOL)

    assert SEARCH_FUNDING_TOOL.name == "search_funding"
    assert SEARCH_FUNDING_TOOL.effect == "external"
    assert "send_email" not in serialized
    assert "score_lead" not in serialized
