from pathlib import Path
from typing import Any

from scholarlead_agent.crossref_models import CrossrefSearchParams, CrossrefWork
from scholarlead_agent.services.crossref_service import CrossrefRunResult
from scholarlead_agent.tools.crossref_tool import (
    SEARCH_CROSSREF_TOOL,
    search_crossref,
)


def make_result(params: CrossrefSearchParams, *, status: str = "success") -> CrossrefRunResult:
    work = CrossrefWork(
        source="crossref",
        crossref_id="10.1038/abc123",
        doi="10.1038/abc123",
        title="CRISPR imaging in cancer",
        abstract="",
        journal="Nature",
        publisher="Springer Nature",
        publication_date="2024-05-02",
        publication_year=2024,
        authors=["Lei S Qi"],
        funder_names=["National Institutes of Health"],
        reference_count=12,
        is_referenced_by_count=34,
        source_url="https://doi.org/10.1038/abc123",
        raw_record_path="raw.json",
    )
    errors = [] if status == "success" else [
        {"stage": "search", "type": "RuntimeError", "message": "Crossref failed"}
    ]
    return CrossrefRunResult(
        task_id="crossref-test",
        status=status,
        search_params=params,
        works=[work] if status == "success" else [],
        raw_paths=None,  # type: ignore[arg-type]
        processed_paths=None,  # type: ignore[arg-type]
        raw_files={"works_json": "raw.json"},
        processed_files={"works_json": "works.json", "works_csv": "works.csv"},
        run_report_path=Path("report.json"),
        run_report={},
        errors=errors,
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )


def fake_runner(params: CrossrefSearchParams) -> CrossrefRunResult:
    return make_result(params)


def test_search_crossref_tool_returns_structured_result() -> None:
    result = search_crossref(
        {
            "doi": "https://doi.org/10.1038/ABC123",
            "title": "ignored",
            "max_results": 5,
        },
        service_runner=fake_runner,
    )

    assert result.success is True
    assert result.source == "crossref"
    assert result.data["doi"] == "10.1038/abc123"
    assert result.data["work_count"] == 1
    assert result.data["works"][0]["funder_names"] == ["National Institutes of Health"]
    assert result.data["lead_generation_status"] == "not_enabled_in_stage21a"
    assert result.data["scoring_status"] == "not_enabled_in_stage21a"
    assert result.data["email_status"] == "not_enabled_in_stage21a"


def test_search_crossref_tool_rejects_invalid_arguments() -> None:
    result = search_crossref({"title": "", "max_results": 5}, service_runner=fake_runner)

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert "doi or title is required" in (result.error_message or "")


def test_search_crossref_tool_converts_failed_run_result() -> None:
    def failed_runner(params: CrossrefSearchParams) -> CrossrefRunResult:
        return make_result(params, status="failed")

    result = search_crossref(
        {"title": "CRISPR", "max_results": 5},
        service_runner=failed_runner,
    )

    assert result.success is False
    assert result.error_code == "crossref_search_failed"
    assert result.errors[0]["stage"] == "search"


def test_crossref_tool_schema_has_no_lead_scoring_or_send_action() -> None:
    serialized = str(SEARCH_CROSSREF_TOOL)

    assert SEARCH_CROSSREF_TOOL.name == "search_crossref"
    assert SEARCH_CROSSREF_TOOL.effect == "external"
    assert "send_email" not in serialized
    assert "generate_lead" not in serialized
    assert "score_lead" not in serialized
