"""Reusable NIH RePORTER funding workflow service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from scholarlead_agent.nih_reporter_client import NIHReporterClient
from scholarlead_agent.nih_reporter_models import (
    NIHFundingRecord,
    NIHReporterSearchParams,
)
from scholarlead_agent.nih_reporter_parser import (
    deduplicate_nih_funding_records,
    parse_nih_reporter_funding_records,
)
from scholarlead_agent.nih_reporter_storage import (
    NIHReporterProcessedOutputPaths,
    NIHReporterRawOutputPaths,
    build_nih_reporter_processed_output_paths,
    build_nih_reporter_raw_output_paths,
    build_nih_reporter_request_meta,
    build_nih_reporter_run_report,
    build_nih_reporter_run_report_path,
    save_nih_reporter_processed_outputs,
    save_nih_reporter_raw_response,
    save_nih_reporter_request_meta,
    save_nih_reporter_run_report,
)
from scholarlead_agent.unified_converters import nih_funding_record_to_unified_funding
from scholarlead_agent.unified_models import UnifiedFunding


class NIHReporterWorkflowClient(Protocol):
    """Protocol for NIH RePORTER clients used by the service."""

    def search_projects(self, params: NIHReporterSearchParams) -> dict[str, Any]:
        """Return the raw NIH RePORTER Projects response."""


@dataclass(frozen=True)
class NIHReporterRunResult:
    """Structured result from one NIH RePORTER run."""

    task_id: str
    status: str
    search_params: NIHReporterSearchParams
    funding_records: list[NIHFundingRecord]
    unified_funding: list[UnifiedFunding]
    raw_paths: NIHReporterRawOutputPaths
    processed_paths: NIHReporterProcessedOutputPaths
    raw_files: dict[str, str]
    processed_files: dict[str, str]
    run_report_path: Path
    run_report: dict[str, Any]
    errors: list[dict[str, str]]
    started_at: str
    finished_at: str


def run_nih_reporter_search(
    params: NIHReporterSearchParams,
    *,
    client: NIHReporterWorkflowClient | None = None,
    timestamp: str | None = None,
    task_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> NIHReporterRunResult:
    """Run the NIH RePORTER first funding workflow end to end."""

    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_task_id = task_id or f"nih-reporter-{run_timestamp}"
    run_started_at = started_at or datetime.now().isoformat(timespec="seconds")
    reporter_client = client or NIHReporterClient()

    raw_paths = build_nih_reporter_raw_output_paths(
        query_label=params.query_label,
        raw_dir=params.raw_dir,
        timestamp=run_timestamp,
    )
    processed_paths = build_nih_reporter_processed_output_paths(
        query_label=params.query_label,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    )
    run_report_path = build_nih_reporter_run_report_path(
        query_label=params.query_label,
        processed_dir=params.processed_dir,
        timestamp=run_timestamp,
    ).run_report_json

    errors: list[dict[str, str]] = []
    funding_records: list[NIHFundingRecord] = []
    unified_funding: list[UnifiedFunding] = []
    status = "success"

    try:
        raw_response = reporter_client.search_projects(params)
        save_nih_reporter_raw_response(raw_response, raw_paths.projects_json)
        _save_request_meta(params, raw_paths, status=status, errors=errors)
    except Exception as error:
        errors.append(_build_error("search", error))
        status = "failed"
        _save_request_meta(params, raw_paths, status=status, errors=errors)
        run_report = _save_report(
            params=params,
            task_id=run_task_id,
            records=funding_records,
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
            funding_records=funding_records,
            unified_funding=unified_funding,
            raw_paths=raw_paths,
            processed_paths=processed_paths,
            run_report_path=run_report_path,
            run_report=run_report,
            errors=errors,
        )

    try:
        parsed = parse_nih_reporter_funding_records(
            raw_response,
            raw_record_path=str(raw_paths.projects_json),
        )
        funding_records = deduplicate_nih_funding_records(parsed)
        unified_funding = [
            nih_funding_record_to_unified_funding(record)
            for record in funding_records
        ]
        save_nih_reporter_processed_outputs(
            records=funding_records,
            paths=processed_paths,
        )
    except Exception as error:
        errors.append(_build_error("processing", error))
        status = "partial_failure"

    run_report = _save_report(
        params=params,
        task_id=run_task_id,
        records=funding_records,
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
        funding_records=funding_records,
        unified_funding=unified_funding,
        raw_paths=raw_paths,
        processed_paths=processed_paths,
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
    )


def _save_request_meta(
    params: NIHReporterSearchParams,
    raw_paths: NIHReporterRawOutputPaths,
    *,
    status: str,
    errors: list[dict[str, str]],
) -> None:
    meta = build_nih_reporter_request_meta(
        params=params,
        paths=raw_paths,
        status=status,
        errors=[error["message"] for error in errors],
    )
    save_nih_reporter_request_meta(meta, raw_paths.request_meta_json)


def _save_report(
    *,
    params: NIHReporterSearchParams,
    task_id: str,
    records: list[NIHFundingRecord],
    raw_paths: NIHReporterRawOutputPaths,
    processed_paths: NIHReporterProcessedOutputPaths | None,
    errors: list[dict[str, str]],
    started_at: str,
    finished_at: str | None,
    status: str,
    run_report_path: Path,
) -> dict[str, Any]:
    report = build_nih_reporter_run_report(
        params=params,
        task_id=task_id,
        records=records,
        raw_files=raw_paths,
        processed_files=processed_paths,
        errors=errors,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
    )
    save_nih_reporter_run_report(report, run_report_path)
    return report


def _build_run_result(
    *,
    task_id: str,
    status: str,
    search_params: NIHReporterSearchParams,
    funding_records: list[NIHFundingRecord],
    unified_funding: list[UnifiedFunding],
    raw_paths: NIHReporterRawOutputPaths,
    processed_paths: NIHReporterProcessedOutputPaths,
    run_report_path: Path,
    run_report: dict[str, Any],
    errors: list[dict[str, str]],
) -> NIHReporterRunResult:
    return NIHReporterRunResult(
        task_id=task_id,
        status=status,
        search_params=search_params,
        funding_records=funding_records,
        unified_funding=unified_funding,
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
