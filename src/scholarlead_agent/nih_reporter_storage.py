"""Storage helpers for NIH RePORTER raw and processed data."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from scholarlead_agent.nih_reporter_models import (
    NIHFundingRecord,
    NIHReporterSearchParams,
)


@dataclass(frozen=True)
class NIHReporterRawOutputPaths:
    """Raw output paths created for one NIH RePORTER run."""

    projects_json: Path
    request_meta_json: Path


@dataclass(frozen=True)
class NIHReporterProcessedOutputPaths:
    """Processed output paths created for one NIH RePORTER run."""

    funding_json: Path
    funding_csv: Path


@dataclass(frozen=True)
class NIHReporterRunReportPath:
    """Run report output path created for one NIH RePORTER run."""

    run_report_json: Path


def build_nih_reporter_raw_output_paths(
    *,
    query_label: str,
    raw_dir: Path,
    timestamp: str | None = None,
) -> NIHReporterRawOutputPaths:
    """Build raw NIH RePORTER output paths."""

    base_name = _build_base_name(query_label, timestamp)
    return NIHReporterRawOutputPaths(
        projects_json=raw_dir / f"nih_reporter_{base_name}_projects.json",
        request_meta_json=raw_dir / f"nih_reporter_{base_name}_request_meta.json",
    )


def build_nih_reporter_processed_output_paths(
    *,
    query_label: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> NIHReporterProcessedOutputPaths:
    """Build processed NIH RePORTER JSON/CSV output paths."""

    base_name = _build_base_name(query_label, timestamp)
    return NIHReporterProcessedOutputPaths(
        funding_json=processed_dir / f"nih_reporter_funding_{base_name}.json",
        funding_csv=processed_dir / f"nih_reporter_funding_{base_name}.csv",
    )


def build_nih_reporter_run_report_path(
    *,
    query_label: str,
    processed_dir: Path,
    timestamp: str | None = None,
) -> NIHReporterRunReportPath:
    """Build a NIH RePORTER run report output path."""

    base_name = _build_base_name(query_label, timestamp)
    return NIHReporterRunReportPath(
        run_report_json=processed_dir / f"nih_reporter_run_report_{base_name}.json"
    )


def save_nih_reporter_raw_response(raw_response: dict[str, Any], path: Path) -> None:
    """Save the raw NIH RePORTER JSON response."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(raw_response, ensure_ascii=False, indent=2))


def build_nih_reporter_request_meta(
    *,
    params: NIHReporterSearchParams,
    paths: NIHReporterRawOutputPaths,
    collected_at: str | None = None,
    status: str = "success",
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build metadata describing one NIH RePORTER collection attempt."""

    return {
        "source": "nih_reporter",
        "pi_name": params.pi_name,
        "institution": params.institution,
        "keyword": params.keyword,
        "from_year": params.from_year,
        "to_year": params.to_year,
        "max_results": params.max_results,
        "collected_at": collected_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "raw_files": {"projects_json": str(paths.projects_json)},
        "coverage_note": "NIH RePORTER only covers NIH-related funding records.",
        "errors": errors or [],
    }


def save_nih_reporter_request_meta(meta: dict[str, Any], path: Path) -> None:
    """Save NIH RePORTER request metadata as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(meta, ensure_ascii=False, indent=2))


def save_nih_reporter_processed_outputs(
    *,
    records: list[NIHFundingRecord],
    paths: NIHReporterProcessedOutputPaths,
) -> None:
    """Save processed NIH funding records as JSON and CSV."""

    save_nih_funding_json(records, paths.funding_json)
    save_nih_funding_csv(records, paths.funding_csv)


def save_nih_funding_json(records: list[NIHFundingRecord], path: Path) -> None:
    """Save processed NIH funding records as stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(
        path,
        json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2),
    )


def save_nih_funding_csv(records: list[NIHFundingRecord], path: Path) -> None:
    """Save processed NIH funding records as Excel-friendly CSV."""

    fieldnames = [
        "Source",
        "Grant_ID",
        "Agency",
        "Project_Title",
        "PI_Name",
        "Institution",
        "Fiscal_Year",
        "Project_Start",
        "Project_End",
        "Amount",
        "Source_URL",
        "Raw_Record_Path",
    ]
    rows = [_record_to_csv_row(record) for record in records]
    _write_csv(path, fieldnames=fieldnames, rows=rows)


def build_nih_reporter_run_report(
    *,
    params: NIHReporterSearchParams,
    task_id: str,
    records: list[NIHFundingRecord],
    raw_files: NIHReporterRawOutputPaths | dict[str, Any] | None,
    processed_files: NIHReporterProcessedOutputPaths | dict[str, Any] | None,
    errors: list[dict[str, Any] | str] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    status: str = "success",
) -> dict[str, Any]:
    """Build an auditable NIH RePORTER run report."""

    return {
        "task_id": task_id,
        "source": "nih_reporter",
        "pi_name": params.pi_name,
        "institution": params.institution,
        "keyword": params.keyword,
        "from_year": params.from_year,
        "to_year": params.to_year,
        "max_results": params.max_results,
        "funding_count": len(records),
        "raw_files": _paths_to_dict(raw_files),
        "processed_files": _paths_to_dict(processed_files),
        "errors": _normalize_report_errors(errors),
        "started_at": started_at,
        "finished_at": finished_at or datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "queried_sources": ["nih_reporter"],
        "coverage_note": "NIH RePORTER only covers NIH-related funding records.",
        "lead_generation_status": "not_enabled_in_stage21d",
        "official_scoring_status": "not_enabled_in_stage21d",
        "email_status": "not_enabled_in_stage21d",
    }


def save_nih_reporter_run_report(report: dict[str, Any], path: Path) -> None:
    """Save a NIH RePORTER run report as JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomically(path, json.dumps(report, ensure_ascii=False, indent=2))


def _record_to_csv_row(record: NIHFundingRecord) -> dict[str, Any]:
    return {
        "Source": record.source,
        "Grant_ID": record.grant_id,
        "Agency": record.agency,
        "Project_Title": record.project_title,
        "PI_Name": record.pi_name,
        "Institution": record.institution,
        "Fiscal_Year": _empty_if_none(record.fiscal_year),
        "Project_Start": record.project_start,
        "Project_End": record.project_end,
        "Amount": _empty_if_none(record.amount),
        "Source_URL": record.source_url,
        "Raw_Record_Path": record.raw_record_path or "",
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
    return safe_value or "nih_reporter"


def _empty_if_none(value: Any) -> Any:
    return "" if value is None else value


def _write_text_atomically(path: Path, content: str) -> None:
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
