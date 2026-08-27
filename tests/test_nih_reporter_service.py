import json
from pathlib import Path
from typing import Any

from scholarlead_agent.nih_reporter_models import NIHReporterSearchParams
from scholarlead_agent.services.nih_reporter_service import run_nih_reporter_search


class FakeNIHReporterClient:
    def __init__(
        self,
        raw_response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.raw_response = raw_response or {"results": []}
        self.error = error
        self.calls: list[NIHReporterSearchParams] = []

    def search_projects(self, params: NIHReporterSearchParams) -> dict[str, Any]:
        self.calls.append(params)
        if self.error is not None:
            raise self.error
        return self.raw_response


def sample_response() -> dict[str, Any]:
    return {
        "results": [
            {
                "appl_id": 123456,
                "project_num": "R01CA123456",
                "project_title": "CRISPR imaging of cancer cells",
                "fiscal_year": 2026,
                "organization": {"org_name": "Stanford University"},
                "principal_investigators": [{"full_name": "Lei S Qi"}],
                "award_amount": 250000,
                "project_start_date": "2025-07-01",
                "project_end_date": "2027-06-30",
                "agency_ic_admin": {"abbreviation": "NCI"},
            }
        ]
    }


def make_params(tmp_path: Path) -> NIHReporterSearchParams:
    return NIHReporterSearchParams(
        pi_name="Lei S Qi",
        institution="Stanford University",
        keyword="CRISPR imaging",
        from_year=2025,
        to_year=2026,
        max_results=5,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )


def test_run_nih_reporter_search_saves_raw_processed_and_report(
    tmp_path: Path,
) -> None:
    client = FakeNIHReporterClient(sample_response())

    result = run_nih_reporter_search(
        make_params(tmp_path),
        client=client,
        timestamp="20260824_120000_000000",
        task_id="nih-reporter-test",
        started_at="2026-08-24T12:00:00",
        finished_at="2026-08-24T12:00:01",
    )

    assert result.status == "success"
    assert len(result.funding_records) == 1
    assert result.funding_records[0].grant_id == "R01CA123456"
    assert result.raw_paths.projects_json.exists()
    assert result.raw_paths.request_meta_json.exists()
    assert result.processed_paths.funding_json.exists()
    assert result.processed_paths.funding_csv.exists()
    assert result.run_report_path.exists()
    assert result.raw_files["projects_json"].endswith("_projects.json")
    assert result.processed_files["funding_json"].endswith(".json")
    assert result.unified_funding[0].agency == "NCI"

    saved_records = json.loads(
        result.processed_paths.funding_json.read_text(encoding="utf-8")
    )
    report = json.loads(result.run_report_path.read_text(encoding="utf-8"))
    assert saved_records[0]["project_title"] == "CRISPR imaging of cancer cells"
    assert report["funding_count"] == 1
    assert report["lead_generation_status"] == "not_enabled_in_stage21d"
    assert report["official_scoring_status"] == "not_enabled_in_stage21d"
    assert report["email_status"] == "not_enabled_in_stage21d"


def test_run_nih_reporter_search_preserves_failure_report_without_processed_files(
    tmp_path: Path,
) -> None:
    result = run_nih_reporter_search(
        make_params(tmp_path),
        client=FakeNIHReporterClient(error=RuntimeError("NIH RePORTER down")),
        timestamp="20260824_120000_000000",
        task_id="nih-reporter-failed",
        started_at="2026-08-24T12:00:00",
        finished_at="2026-08-24T12:00:01",
    )

    assert result.status == "failed"
    assert result.funding_records == []
    assert result.raw_paths.request_meta_json.exists()
    assert result.run_report_path.exists()
    assert not result.processed_files
    assert result.errors[0]["stage"] == "search"
    assert "NIH RePORTER down" in result.errors[0]["message"]


def test_run_nih_reporter_search_handles_empty_results(tmp_path: Path) -> None:
    result = run_nih_reporter_search(
        make_params(tmp_path),
        client=FakeNIHReporterClient({"results": []}),
    )

    assert result.status == "success"
    assert result.funding_records == []
    assert result.processed_paths.funding_json.exists()
