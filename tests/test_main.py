import json
from pathlib import Path
from typing import Any

from literature_agent.main import main
from literature_agent.works import SearchParams


class FakeOpenAlexClient:
    captured_params: SearchParams | None = None

    def __init__(self, config: object) -> None:
        self.config = config

    def fetch_works(self, params: SearchParams) -> dict[str, Any]:
        FakeOpenAlexClient.captured_params = params
        return {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.1000/ABC",
                    "title": "CLI title",
                    "abstract_inverted_index": {"CLI": [0], "abstract": [1]},
                    "publication_date": "2024-01-01",
                    "authorships": [],
                }
            ]
        }


def test_main_collects_and_writes_outputs(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    monkeypatch.setattr("literature_agent.main.OpenAlexClient", FakeOpenAlexClient)

    exit_code = main(
        [
            "--query",
            "genome assembly",
            "--from-date",
            "2024-01-01",
            "--to-date",
            "2024-12-31",
            "--max-results",
            "3",
            "--raw-dir",
            str(tmp_path / "raw"),
            "--processed-dir",
            str(tmp_path / "processed"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Collected 1 records" in captured.out
    assert FakeOpenAlexClient.captured_params == SearchParams(
        query="genome assembly",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=3,
    )

    raw_files = list((tmp_path / "raw").glob("*_raw.json"))
    processed_json_files = list((tmp_path / "processed").glob("*_processed.json"))
    processed_csv_files = list((tmp_path / "processed").glob("*_processed.csv"))

    assert len(raw_files) == 1
    assert len(processed_json_files) == 1
    assert len(processed_csv_files) == 1

    processed_data = json.loads(processed_json_files[0].read_text(encoding="utf-8"))
    assert processed_data[0]["doi"] == "10.1000/abc"
    assert processed_data[0]["abstract"] == "CLI abstract"
