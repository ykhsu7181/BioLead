import csv
import json
from pathlib import Path

from scholarlead_agent.storage import (
    build_output_paths,
    save_processed_records,
    save_raw_response,
)
from scholarlead_agent.works import PaperRecord


def test_save_raw_and_processed_outputs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    processed_dir = tmp_path / "processed"
    paths = build_output_paths(
        query="genome assembly",
        raw_dir=raw_dir,
        processed_dir=processed_dir,
        timestamp="20260723_120000",
    )
    record = PaperRecord(
        openalex_id="https://openalex.org/W1",
        doi="10.1000/abc",
        title="A title",
        abstract="An abstract",
        publication_date="2024-01-01",
        authors=["Alice", "Bob"],
        institutions=["Institute A"],
    )

    save_raw_response({"results": [{"id": "W1"}]}, paths.raw_json)
    save_processed_records([record], paths)

    assert paths.raw_json.name == "genome_assembly_20260723_120000_raw.json"
    assert json.loads(paths.raw_json.read_text(encoding="utf-8")) == {
        "results": [{"id": "W1"}]
    }
    processed_json = json.loads(paths.processed_json.read_text(encoding="utf-8"))
    assert processed_json[0]["authors"] == ["Alice", "Bob"]

    with paths.processed_csv.open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert rows[0]["doi"] == "10.1000/abc"
    assert rows[0]["authors"] == "Alice; Bob"
    assert rows[0]["institutions"] == "Institute A"

