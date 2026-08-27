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
    request_meta_json: Path | None = None


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
        request_meta_json=raw_dir / f"{base_name}_request_meta.json",
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


def build_openalex_request_meta(
    *,
    query: str,
    from_date: str,
    to_date: str,
    max_results: int,
    paths: OutputPaths,
    collected_at: str | None = None,
    status: str = "success",
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata describing one OpenAlex raw collection attempt."""

    return {
        "source": "openalex",
        "query": query,
        "from_date": from_date,
        "to_date": to_date,
        "max_results": max_results,
        "collected_at": collected_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "raw_files": {"raw_json": str(paths.raw_json)},
        "errors": errors or [],
    }


def save_openalex_request_meta(meta: dict[str, Any], path: Path | None) -> None:
    """Save OpenAlex request metadata as JSON when a path is available."""

    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(meta, ensure_ascii=False, indent=2))


def build_openalex_run_report_path(
    query: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> Path:
    """Build a run report path for one OpenAlex run."""

    safe_query = _safe_filename_part(query)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return processed_dir / f"openalex_run_report_{safe_query}_{run_timestamp}.json"


def build_openalex_run_report(
    *,
    query: str,
    from_date: str,
    to_date: str,
    max_results: int,
    task_id: str,
    records: list[PaperRecord],
    raw_files: OutputPaths | dict[str, Any] | None,
    processed_files: OutputPaths | dict[str, Any] | None,
    errors: list[dict[str, Any] | str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Build an auditable OpenAlex run report."""

    return {
        "task_id": task_id,
        "source": "openalex",
        "query": query,
        "from_date": from_date,
        "to_date": to_date,
        "max_results": max_results,
        "work_count": len(records),
        "unified_paper_count": len(records),
        "raw_files": _paths_to_dict(raw_files, include_request_meta=True),
        "processed_files": _paths_to_dict(processed_files),
        "errors": _normalize_report_errors(errors),
        "started_at": started_at,
        "finished_at": finished_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "queried_sources": ["openalex"],
        "lead_generation_status": "not_enabled_in_stage21c",
        "scoring_status": "not_enabled_in_stage21c",
        "email_status": "not_enabled_in_stage21c",
    }


def save_openalex_run_report(report: dict[str, Any], path: Path) -> None:
    """Save an OpenAlex run report as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(report, ensure_ascii=False, indent=2))


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


def _paths_to_dict(
    paths: Any,
    *,
    include_request_meta: bool = False,
) -> dict[str, str]:
    if paths is None:
        return {}
    if isinstance(paths, dict):
        return {
            str(key): str(value)
            for key, value in paths.items()
            if value is not None and str(value)
        }

    field_names = ["raw_json", "processed_json", "processed_csv"]
    if include_request_meta:
        field_names.append("request_meta_json")

    path_values: dict[str, str] = {}
    for field_name in field_names:
        value = getattr(paths, field_name, None)
        if value is not None:
            path_values[field_name] = str(value)
    return path_values


def _normalize_report_errors(
    errors: list[dict[str, Any] | str] | None,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for error in errors or []:
        if isinstance(error, dict):
            normalized.append(
                {
                    "stage": str(error.get("stage") or "unknown"),
                    "type": str(error.get("type") or "unknown"),
                    "message": str(error.get("message") or ""),
                }
            )
            continue
        normalized.append(
            {"stage": "unknown", "type": "unknown", "message": str(error)}
        )
    return normalized


def _write_text_atomically(path: Path, content: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def _safe_filename_part(value: str) -> str:
    safe_value = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE)
    safe_value = safe_value.strip("_")[:50]
    return safe_value or "search"

