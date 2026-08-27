"""Reusable OpenAlex workflow service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from scholarlead_agent.openalex_client import OpenAlexClient
from scholarlead_agent.storage import (
    OutputPaths,
    build_openalex_request_meta,
    build_openalex_run_report,
    build_openalex_run_report_path,
    build_output_paths,
    save_openalex_request_meta,
    save_openalex_run_report,
    save_processed_records,
    save_raw_response,
)
from scholarlead_agent.unified_converters import openalex_record_to_unified_paper
from scholarlead_agent.unified_models import UnifiedPaper
from scholarlead_agent.works import PaperRecord, SearchParams, clean_works_response


class OpenAlexWorkflowClient(Protocol):
    """Protocol for OpenAlex clients used by the service."""

    def fetch_works(self, params: SearchParams) -> dict[str, Any]:
        """Return the raw OpenAlex Works response."""


@dataclass(frozen=True)
class OpenAlexRunResult:
    """Structured result from one OpenAlex run."""

    task_id: str
    status: str
    search_params: SearchParams
    works: list[PaperRecord]
    unified_papers: list[UnifiedPaper]
    output_paths: OutputPaths
    raw_files: dict[str, str]
    processed_files: dict[str, str]
    run_report_path: Path
    run_report: dict[str, Any]
    errors: list[dict[str, str]]
    started_at: str
    finished_at: str


def run_openalex_search(
    params: SearchParams,
    *,
    client: OpenAlexWorkflowClient | None = None,
    raw_dir: Path | str = Path("data/raw/openalex"),
    processed_dir: Path | str = Path("data/processed/openalex"),
    timestamp: str | None = None,
    task_id: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
) -> OpenAlexRunResult:
    """Run the OpenAlex workflow end to end."""

    run_timestamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_task_id = task_id or f"openalex-{run_timestamp}"
    run_started_at = started_at or datetime.now().isoformat(timespec="seconds")
    openalex_client = client or OpenAlexClient()
    output_paths = build_output_paths(
        query=params.query,
        raw_dir=Path(raw_dir),
        processed_dir=Path(processed_dir),
        timestamp=run_timestamp,
    )
    run_report_path = build_openalex_run_report_path(
        query=params.query,
        processed_dir=Path(processed_dir),
        timestamp=run_timestamp,
    )

    errors: list[dict[str, str]] = []
    works: list[PaperRecord] = []
    unified_papers: list[UnifiedPaper] = []
    status = "success"

    try:
        raw_response = openalex_client.fetch_works(params)
        save_raw_response(raw_response, output_paths.raw_json)
        _save_request_meta(params, output_paths, status=status, errors=errors)
    except Exception as error:
        errors.append(_build_error("fetch", error))
        status = "failed"
        _save_request_meta(params, output_paths, status=status, errors=errors)
        run_report = _save_report(
            params=params,
            task_id=run_task_id,
            works=works,
            output_paths=output_paths,
            processed_files=None,
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
            unified_papers=unified_papers,
            output_paths=output_paths,
            run_report_path=run_report_path,
            run_report=run_report,
            errors=errors,
        )

    try:
        works = clean_works_response(raw_response)
        save_processed_records(works, output_paths)
        unified_papers = [
            openalex_record_to_unified_paper(
                work,
                retrieved_at=run_started_at,
                raw_record_path=str(output_paths.raw_json),
            )
            for work in works
        ]
    except Exception as error:
        errors.append(_build_error("processing", error))
        status = "partial_failure"

    run_report = _save_report(
        params=params,
        task_id=run_task_id,
        works=works,
        output_paths=output_paths,
        processed_files=output_paths if status == "success" else None,
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
        unified_papers=unified_papers,
        output_paths=output_paths,
        run_report_path=run_report_path,
        run_report=run_report,
        errors=errors,
    )


def _save_request_meta(
    params: SearchParams,
    output_paths: OutputPaths,
    *,
    status: str,
    errors: list[dict[str, str]],
) -> None:
    meta = build_openalex_request_meta(
        query=params.query,
        from_date=params.from_date,
        to_date=params.to_date,
        max_results=params.max_results,
        paths=output_paths,
        status=status,
        errors=[error["message"] for error in errors],
    )
    save_openalex_request_meta(meta, output_paths.request_meta_json)


def _save_report(
    *,
    params: SearchParams,
    task_id: str,
    works: list[PaperRecord],
    output_paths: OutputPaths,
    processed_files: OutputPaths | None,
    errors: list[dict[str, str]],
    started_at: str,
    finished_at: str | None,
    status: str,
    run_report_path: Path,
) -> dict[str, Any]:
    report = build_openalex_run_report(
        query=params.query,
        from_date=params.from_date,
        to_date=params.to_date,
        max_results=params.max_results,
        task_id=task_id,
        records=works,
        raw_files=output_paths,
        processed_files=processed_files,
        errors=errors,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
    )
    save_openalex_run_report(report, run_report_path)
    return report


def _build_run_result(
    *,
    task_id: str,
    status: str,
    search_params: SearchParams,
    works: list[PaperRecord],
    unified_papers: list[UnifiedPaper],
    output_paths: OutputPaths,
    run_report_path: Path,
    run_report: dict[str, Any],
    errors: list[dict[str, str]],
) -> OpenAlexRunResult:
    return OpenAlexRunResult(
        task_id=task_id,
        status=status,
        search_params=search_params,
        works=works,
        unified_papers=unified_papers,
        output_paths=output_paths,
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
