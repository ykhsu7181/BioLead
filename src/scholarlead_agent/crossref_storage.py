"""Storage helpers for Crossref raw and processed data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scholarlead_agent.crossref_models import CrossrefSearchParams, CrossrefWork


@dataclass(frozen=True)
class CrossrefRawOutputPaths:
    """Raw output paths created for one Crossref collection run."""

    works_json: Path
    request_meta_json: Path


@dataclass(frozen=True)
class CrossrefProcessedOutputPaths:
    """Processed output paths created for one Crossref collection run."""

    works_json: Path
    works_csv: Path


@dataclass(frozen=True)
class CrossrefRunReportPath:
    """Run report output path created for one Crossref collection run."""

    run_report_json: Path


def build_crossref_raw_output_paths(
    *,
    query_label: str,
    raw_dir: Path,
    timestamp: str | None = None,
) -> CrossrefRawOutputPaths:
    """Build raw Crossref output paths for a DOI or title query."""

    base_name = _build_base_name(query_label, timestamp)
    return CrossrefRawOutputPaths(
        works_json=raw_dir / f"crossref_{base_name}_works.json",
        request_meta_json=raw_dir / f"crossref_{base_name}_request_meta.json",
    )


def build_crossref_processed_output_paths(
    *,
    query_label: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> CrossrefProcessedOutputPaths:
    """Build processed Crossref JSON/CSV output paths."""

    base_name = _build_base_name(query_label, timestamp)
    return CrossrefProcessedOutputPaths(
        works_json=processed_dir / f"crossref_works_{base_name}.json",
        works_csv=processed_dir / f"crossref_works_{base_name}.csv",
    )


def build_crossref_run_report_path(
    *,
    query_label: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> CrossrefRunReportPath:
    """Build a Crossref run report output path."""

    base_name = _build_base_name(query_label, timestamp)
    return CrossrefRunReportPath(
        run_report_json=processed_dir / f"crossref_run_report_{base_name}.json"
    )


def save_crossref_raw_response(raw_response: dict[str, Any], path: Path) -> None:
    """Save the raw Crossref JSON response."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(raw_response, ensure_ascii=False, indent=2))


def build_crossref_request_meta(
    *,
    params: CrossrefSearchParams,
    paths: CrossrefRawOutputPaths,
    collected_at: str | None = None,
    status: str = "success",
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata describing one Crossref raw collection attempt."""

    return {
        "source": "crossref",
        "doi": params.doi,
        "title": params.title,
        "max_results": params.max_results,
        "collected_at": collected_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "raw_files": {"works_json": str(paths.works_json)},
        "errors": errors or [],
    }


def save_crossref_request_meta(meta: dict[str, Any], path: Path) -> None:
    """Save Crossref request metadata as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(meta, ensure_ascii=False, indent=2))


def save_crossref_processed_outputs(
    *,
    works: list[CrossrefWork],
    paths: CrossrefProcessedOutputPaths,
) -> None:
    """Save processed Crossref works as JSON and CSV."""

    save_crossref_works_json(works, paths.works_json)
    save_crossref_works_csv(works, paths.works_csv)


def save_crossref_works_json(works: list[CrossrefWork], path: Path) -> None:
    """Save processed Crossref works as stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(
        path,
        json.dumps([work.to_dict() for work in works], ensure_ascii=False, indent=2),
    )


def save_crossref_works_csv(works: list[CrossrefWork], path: Path) -> None:
    """Save processed Crossref works as Excel-friendly CSV."""

    fieldnames = [
        "Source",
        "Crossref_ID",
        "DOI",
        "Title",
        "Abstract",
        "Journal",
        "Publisher",
        "Publication_Date",
        "Publication_Year",
        "Authors",
        "Funder_Names",
        "Reference_Count",
        "Is_Referenced_By_Count",
        "Source_URL",
        "Raw_Record_Path",
    ]
    rows = [_crossref_work_to_csv_row(work) for work in works]
    _write_csv(path, fieldnames=fieldnames, rows=rows)


def build_crossref_run_report(
    *,
    params: CrossrefSearchParams,
    task_id: str,
    works: list[CrossrefWork],
    raw_files: CrossrefRawOutputPaths | dict[str, Any] | None,
    processed_files: CrossrefProcessedOutputPaths | dict[str, Any] | None,
    errors: list[dict[str, Any] | str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Build an auditable Crossref run report."""

    return {
        "task_id": task_id,
        "source": "crossref",
        "doi": params.doi,
        "title": params.title,
        "max_results": params.max_results,
        "work_count": len(works),
        "raw_files": _paths_to_dict(raw_files),
        "processed_files": _paths_to_dict(processed_files),
        "errors": _normalize_report_errors(errors),
        "started_at": started_at,
        "finished_at": finished_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "queried_sources": ["crossref"],
        "lead_generation_status": "not_enabled_in_stage21a",
        "scoring_status": "not_enabled_in_stage21a",
        "email_status": "not_enabled_in_stage21a",
    }


def save_crossref_run_report(report: dict[str, Any], path: Path) -> None:
    """Save a Crossref run report as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(report, ensure_ascii=False, indent=2))


def _crossref_work_to_csv_row(work: CrossrefWork) -> dict[str, Any]:
    return {
        "Source": work.source,
        "Crossref_ID": work.crossref_id,
        "DOI": work.doi or "",
        "Title": work.title,
        "Abstract": work.abstract,
        "Journal": work.journal,
        "Publisher": work.publisher,
        "Publication_Date": work.publication_date,
        "Publication_Year": _empty_if_none(work.publication_year),
        "Authors": _serialize_list(work.authors),
        "Funder_Names": _serialize_list(work.funder_names),
        "Reference_Count": _empty_if_none(work.reference_count),
        "Is_Referenced_By_Count": _empty_if_none(work.is_referenced_by_count),
        "Source_URL": work.source_url,
        "Raw_Record_Path": work.raw_record_path or "",
    }


def _write_csv(
    path: Path,
    *,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def _paths_to_dict(paths: Any) -> dict[str, str]:
    if paths is None:
        return {}
    if isinstance(paths, dict):
        return {
            str(key): str(value)
            for key, value in paths.items()
            if value is not None and str(value)
        }
    path_values: dict[str, str] = {}
    for field_name in getattr(paths, "__dataclass_fields__", {}):
        value = getattr(paths, field_name)
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


def _build_base_name(query_label: str, timestamp: str | None) -> str:
    safe_query = _safe_filename_part(query_label)
    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"{safe_query}_{run_timestamp}"


def _safe_filename_part(value: str) -> str:
    safe_value = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE)
    safe_value = safe_value.strip("_")[:50]
    return safe_value or "crossref"


def _serialize_list(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=True)


def _empty_if_none(value: Any) -> Any:
    return "" if value is None else value


def _write_text_atomically(path: Path, content: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
