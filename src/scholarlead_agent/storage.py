"""File storage helpers for raw and processed OpenAlex data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scholarlead_agent.works import PaperRecord, records_to_dicts


@dataclass(frozen=True)
class OutputPaths:
    """Paths created for one collection run."""

    raw_json: Path
    processed_json: Path
    processed_csv: Path


def build_output_paths(
    query: str,
    raw_dir: Path,
    processed_dir: Path,
    timestamp: str | None = None,
) -> OutputPaths:
    """Build raw and processed output paths for a query."""

    safe_query = _safe_filename_part(query)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base_name = f"{safe_query}_{run_timestamp}"

    return OutputPaths(
        raw_json=raw_dir / f"{base_name}_raw.json",
        processed_json=processed_dir / f"{base_name}_processed.json",
        processed_csv=processed_dir / f"{base_name}_processed.csv",
    )


def save_raw_response(raw_response: dict[str, Any], path: Path) -> None:
    """Save the raw API response as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(raw_response, ensure_ascii=False, indent=2)
    _write_text_atomically(path, content)


def save_processed_records(records: list[PaperRecord], paths: OutputPaths) -> None:
    """Save processed records as JSON and CSV."""

    paths.processed_json.parent.mkdir(parents=True, exist_ok=True)
    records_as_dicts = records_to_dicts(records)
    json_content = json.dumps(records_as_dicts, ensure_ascii=False, indent=2)
    _write_text_atomically(paths.processed_json, json_content)
    _write_records_csv(records, paths.processed_csv)


def _write_records_csv(records: list[PaperRecord], path: Path) -> None:
    fieldnames = [
        "openalex_id",
        "doi",
        "title",
        "abstract",
        "publication_date",
        "authors",
        "institutions",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")

    with temp_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "openalex_id": record.openalex_id,
                    "doi": record.doi or "",
                    "title": record.title,
                    "abstract": record.abstract,
                    "publication_date": record.publication_date,
                    "authors": "; ".join(record.authors),
                    "institutions": "; ".join(record.institutions),
                }
            )

    temp_path.replace(path)


def _write_text_atomically(path: Path, content: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def _safe_filename_part(value: str) -> str:
    safe_value = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE)
    safe_value = safe_value.strip("_")[:50]
    return safe_value or "search"

