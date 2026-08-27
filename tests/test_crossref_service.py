import json
from pathlib import Path
from typing import Any

from scholarlead_agent.crossref_models import CrossrefSearchParams
from scholarlead_agent.services.crossref_service import run_crossref_search


class FakeCrossrefClient:
    def __init__(
        self,
        raw_response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.raw_response = raw_response or {"message": {"items": []}}
        self.error = error
        self.calls: list[CrossrefSearchParams] = []

    def search_works(self, params: CrossrefSearchParams) -> dict[str, Any]:
        self.calls.append(params)
        if self.error is not None:
            raise self.error
        return self.raw_response


def sample_response() -> dict[str, Any]:
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.1038/ABC123",
                    "title": ["CRISPR imaging in cancer"],
                    "container-title": ["Nature"],
                    "publisher": "Springer Nature",
                    "published-print": {"date-parts": [[2024, 5, 2]]},
                    "author": [{"given": "Lei S", "family": "Qi"}],
                    "funder": [{"name": "National Institutes of Health"}],
                    "reference-count": 12,
                    "is-referenced-by-count": 34,
                    "URL": "https://doi.org/10.1038/ABC123",
                }
            ]
        }
    }


def make_params(tmp_path: Path) -> CrossrefSearchParams:
    return CrossrefSearchParams(
        doi=None,
        title="CRISPR imaging",
        max_results=5,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )


def test_run_crossref_search_saves_raw_processed_and_report(tmp_path: Path) -> None:
    client = FakeCrossrefClient(sample_response())

    result = run_crossref_search(
        make_params(tmp_path),
        client=client,
        timestamp="20260821_120000_000000",
        task_id="crossref-test",
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )

    assert result.status == "success"
    assert len(result.works) == 1
    assert result.works[0].doi == "10.1038/abc123"
    assert result.raw_paths.works_json.exists()
    assert result.raw_paths.request_meta_json.exists()
    assert result.processed_paths.works_json.exists()
    assert result.processed_paths.works_csv.exists()
    assert result.run_report_path.exists()
    assert result.raw_files["works_json"].endswith("_works.json")
    assert result.processed_files["works_json"].endswith(".json")

    saved_works = json.loads(result.processed_paths.works_json.read_text(encoding="utf-8"))
    report = json.loads(result.run_report_path.read_text(encoding="utf-8"))
    assert saved_works[0]["title"] == "CRISPR imaging in cancer"
    assert report["work_count"] == 1
    assert report["lead_generation_status"] == "not_enabled_in_stage21a"
    assert report["scoring_status"] == "not_enabled_in_stage21a"
    assert report["email_status"] == "not_enabled_in_stage21a"


def test_run_crossref_search_preserves_failure_report_without_processed_files(
    tmp_path: Path,
) -> None:
    result = run_crossref_search(
        make_params(tmp_path),
        client=FakeCrossrefClient(error=RuntimeError("Crossref down")),
        timestamp="20260821_120000_000000",
        task_id="crossref-failed",
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )

    assert result.status == "failed"
    assert result.works == []
    assert result.raw_paths.request_meta_json.exists()
    assert result.run_report_path.exists()
    assert not result.processed_files
    assert result.errors[0]["stage"] == "search"
    assert "Crossref down" in result.errors[0]["message"]


def test_run_crossref_search_handles_empty_results(tmp_path: Path) -> None:
    result = run_crossref_search(
        make_params(tmp_path),
        client=FakeCrossrefClient({"message": {"items": []}}),
    )

    assert result.status == "success"
    assert result.works == []
    assert result.processed_paths.works_json.exists()
