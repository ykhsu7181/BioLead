import json
from pathlib import Path
from typing import Any

from scholarlead_agent.services.openalex_service import run_openalex_search
from scholarlead_agent.works import SearchParams


class FakeOpenAlexClient:
    def __init__(
        self,
        raw_response: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.raw_response = raw_response or {"results": []}
        self.error = error
        self.calls: list[SearchParams] = []

    def fetch_works(self, params: SearchParams) -> dict[str, Any]:
        self.calls.append(params)
        if self.error is not None:
            raise self.error
        return self.raw_response


def sample_response() -> dict[str, Any]:
    return {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1000/ABC",
                "title": "Single-cell cancer atlas",
                "abstract_inverted_index": {"Single-cell": [0], "atlas": [1]},
                "publication_date": "2025-03-04",
                "authorships": [
                    {
                        "author": {"display_name": "Alice Smith"},
                        "institutions": [{"display_name": "Example University"}],
                    }
                ],
            }
        ]
    }


def make_params() -> SearchParams:
    return SearchParams(
        query="single-cell cancer",
        from_date="2025-01-01",
        to_date="2025-12-31",
        max_results=5,
    )


def test_run_openalex_search_saves_outputs_and_unified_papers(tmp_path: Path) -> None:
    result = run_openalex_search(
        make_params(),
        client=FakeOpenAlexClient(sample_response()),
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        timestamp="20260821_120000_000000",
        task_id="openalex-test",
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )

    assert result.status == "success"
    assert len(result.works) == 1
    assert result.works[0].doi == "10.1000/abc"
    assert result.works[0].abstract == "Single-cell atlas"
    assert len(result.unified_papers) == 1
    assert result.unified_papers[0].source_name == "openalex"
    assert result.output_paths.raw_json.exists()
    assert result.output_paths.request_meta_json is not None
    assert result.output_paths.request_meta_json.exists()
    assert result.output_paths.processed_json.exists()
    assert result.output_paths.processed_csv.exists()
    assert result.run_report_path.exists()

    saved = json.loads(result.output_paths.processed_json.read_text(encoding="utf-8"))
    report = json.loads(result.run_report_path.read_text(encoding="utf-8"))
    assert saved[0]["openalex_id"] == "https://openalex.org/W1"
    assert report["work_count"] == 1
    assert report["unified_paper_count"] == 1
    assert report["lead_generation_status"] == "not_enabled_in_stage21c"
    assert result.raw_files["raw_json"].endswith("_raw.json")
    assert result.processed_files["processed_json"].endswith("_processed.json")


def test_run_openalex_search_failure_writes_report_without_processed_files(
    tmp_path: Path,
) -> None:
    result = run_openalex_search(
        make_params(),
        client=FakeOpenAlexClient(error=RuntimeError("OpenAlex down")),
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        timestamp="20260821_120000_000000",
        task_id="openalex-failed",
        started_at="2026-08-21T12:00:00",
        finished_at="2026-08-21T12:00:01",
    )

    assert result.status == "failed"
    assert result.works == []
    assert result.unified_papers == []
    assert result.run_report_path.exists()
    assert not result.processed_files
    assert result.errors[0]["stage"] == "fetch"


def test_run_openalex_search_handles_empty_results(tmp_path: Path) -> None:
    result = run_openalex_search(
        make_params(),
        client=FakeOpenAlexClient({"results": []}),
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )

    assert result.status == "success"
    assert result.works == []
    assert result.unified_papers == []
    assert result.output_paths.processed_json.exists()
