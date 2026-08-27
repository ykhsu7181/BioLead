"""Reusable Crossref workflow service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from scholarlead_agent.crossref_client import CrossrefClient
from scholarlead_agent.crossref_models import CrossrefSearchParams, CrossrefWork
from scholarlead_agent.crossref_parser import (
    deduplicate_crossref_works,
    parse_crossref_works,
)
from scholarlead_agent.crossref_storage import (
    CrossrefProcessedOutputPaths,
    CrossrefRawOutputPaths,
    build_crossref_processed_output_paths,
    build_crossref_raw_output_paths,
    build_crossref_request_meta,
    build_crossref_run_report,
    build_crossref_run_report_path,
    save_crossref_processed_outputs,
    save_crossref_raw_response,
    save_crossref_request_meta,
    save_crossref_run_report,
)


class CrossrefWorkflowClient(Protocol):
    """Protocol for Crossref clients used by the service."""

    def search_works(self, params: CrossrefSearchParams) -> dict[str, Any]:
        """Return the raw Crossref Works response."""


@dataclass(frozen=True)
class CrossrefRunResult:
    """Structured result from one Crossref run."""

    task_id: str
    status: str
    search_params: CrossrefSearchParams
    works: list[CrossrefWork]
    raw_paths: CrossrefRawOutputPaths
    processed_paths: CrossrefProcessedOutputPaths
    raw_files: dict[str, str]
    processed_files: dict[str, str]
    run_report_path: Path
    run_report: dict[str, Any]
    errors: list[dict[str, str]]
    started_at: str
    finished_at: str


def run_crossref_search(
    params: CrossrefSearchParams,
    *,
    client: CrossrefWorkflowClient | None = None,
    timestamp: str | None = None,
    task_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> CrossrefRunResult:
    """Run the Crossref first integration workflow end to end."""

    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_task_id = task_id or f"crossref-{run_timestamp}"
    run_started_at = started_at or datetime.now().isoformat(timespec="seconds")
    crossref_client = client or CrossrefClient()

    raw_paths = build_crossref_raw_output_paths(
        query_label=params.query_label,
        raw_dir=params.raw_dir,
        timestamp=run_timestamp,
    )
    processed_paths = build_crossref_processed_output_paths(
        query_label=params.query_label,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    )
    run_report_path = build_crossref_run_report_path(
        query_label=params.query_label,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    ).run_report_json

    errors: list[dict[str, str]] = []
    works: list[CrossrefWork] = []
    status = "success"

    try:
        raw_response = crossref_client.search_works(params)
        save_crossref_raw_response(raw_response, raw_paths.works_json)
        _save_request_meta(params, raw_paths, status=status, errors=errors)
    except Exception as error:
        errors.append(_build_error("search", error))
        status = "failed"
        _save_request_meta(params, raw_paths, status=status, errors=errors)
        run_report = _save_report(
            params=params,
            task_id=run_task_id,
            works=works,
            raw_paths=raw_paths,
            processed_paths=None,
            errors=errors,
            started_at=run_started_at,
            finished_at=finished_at,
            status=status,
            run_report_path=run_report_path,
        )
        return _build_run_result(
            task_id=run_task_id,
            status=status,
            search_params=params,
            works=works,
            raw_paths=raw_paths,
            processed_paths=processed_paths,
            run_report_path=run_report_path,
            run_report=run_report,
            errors=errors,
        )

    try:
        parsed = parse_crossref_works(
            raw_response,
            raw_record_path=str(raw_paths.works_json),
        )
        works = deduplicate_crossref_works(parsed)
        save_crossref_processed_outputs(works=works, paths=processed_paths)
    except Exception as error:
        errors.append(_build_error("processing", error))
        status = "partial_failure"

    run_report = _save_report(
        params=params,
        task_id=run_task_id,
        works=works,
        raw_paths=raw_paths,
        processed_paths=processed_paths if status == "success" else None,
        errors=errors,
        started_at=run_started_at,
        finished_at=finished_at,
        status=status,
        run_report_path=run_report_path,
    )

    return _build_run_result(
        task_id=run_task_id,
        status=status,
        search_params=params,
        works=works,
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
    )


def _save_request_meta(
    params: CrossrefSearchParams,
    raw_paths: CrossrefRawOutputPaths,
    *,
    status: str,
    errors: list[dict[str, str]],
) -> None:
    meta = build_crossref_request_meta(
        params=params,
        paths=raw_paths,
        status=status,
        errors=[error["message"] for error in errors],
    )
    save_crossref_request_meta(meta, raw_paths.request_meta_json)


def _save_report(
    *,
    params: CrossrefSearchParams,
    task_id: str,
    works: list[CrossrefWork],
    raw_paths: CrossrefRawOutputPaths,
    processed_paths: CrossrefProcessedOutputPaths | None,
    errors: list[dict[str, str]],
    started_at: str,
    finished_at: str | None,
    status: str,
    run_report_path: Path,
) -> dict[str, Any]:
    report = build_crossref_run_report(
        params=params,
        task_id=task_id,
        works=works,
        raw_files=raw_paths,
        processed_files=processed_paths,
        errors=errors,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
    )
    save_crossref_run_report(report, run_report_path)
    return report


def _build_run_result(
    *,
    task_id: str,
    status: str,
    search_params: CrossrefSearchParams,
    works: list[CrossrefWork],
    raw_paths: CrossrefRawOutputPaths,
    processed_paths: CrossrefProcessedOutputPaths,
    run_report_path: Path,
    run_report: dict[str, Any],
    errors: list[dict[str, str]],
) -> CrossrefRunResult:
    return CrossrefRunResult(
        task_id=task_id,
        status=status,
        search_params=search_params,
        works=works,
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        raw_files=_string_dict(run_report.get("raw_files", {})),
        processed_files=_string_dict(run_report.get("processed_files", {})),
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
        started_at=str(run_report.get("started_at") or ""),
        finished_at=str(run_report.get("finished_at") or ""),
    )


def _build_error(stage: str, error: Exception) -> dict[str, str]:
    return {
        "stage": stage,
        "type": error.__class__.__name__,
        "message": str(error),
    }


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}
