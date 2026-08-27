"""Agent Tool wrapper for NIH RePORTER funding searches."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.nih_reporter_models import (
    NIHFundingRecord,
    NIHReporterSearchParams,
    NIH_REPORTER_MAX_RESULTS_LIMIT,
    validate_nih_reporter_search_inputs,
)
from scholarlead_agent.services.nih_reporter_service import (
    NIHReporterRunResult,
    run_nih_reporter_search,
)


SEARCH_FUNDING_TOOL_NAME = "search_funding"

SEARCH_FUNDING_DESCRIPTION = (
    "Search NIH RePORTER project funding records by PI name, institution, "
    "keyword, fiscal-year range, and max_results. Use this only as explicit "
    "NIH funding evidence. NIH RePORTER does not cover all funding sources. "
    "This tool does not generate leads, does not run official scoring, and "
    "must not be used to send email or infer funding from papers alone."
)

SEARCH_FUNDING_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["from_year", "to_year", "max_results"],
    "properties": {
        "pi_name": {
            "type": "string",
            "description": "Optional PI name search text.",
        },
        "institution": {
            "type": "string",
            "description": "Optional organization name search text.",
        },
        "keyword": {
            "type": "string",
            "description": "Optional project title, abstract, or term keyword text.",
        },
        "from_year": {
            "type": "integer",
            "minimum": 1900,
            "description": "Start NIH fiscal year.",
        },
        "to_year": {
            "type": "integer",
            "minimum": 1900,
            "description": "End NIH fiscal year.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": NIH_REPORTER_MAX_RESULTS_LIMIT,
            "description": "Maximum NIH RePORTER results.",
        },
    },
}


FundingServiceRunner = Callable[[NIHReporterSearchParams], NIHReporterRunResult]


def search_funding(
    arguments: dict[str, Any],
    *,
    service_runner: FundingServiceRunner = run_nih_reporter_search,
) -> ToolResult:
    """Run the NIH RePORTER service from structured tool-call arguments."""

    try:
        params = _validate_tool_arguments(arguments)
    except ValueError as error:
        return ToolResult(
            success=False,
            source="nih_reporter",
            error_code="invalid_arguments",
            error_message=str(error),
        )

    try:
        result = service_runner(params)
    except Exception as error:
        return ToolResult(
            success=False,
            source="nih_reporter",
            error_code="tool_execution_error",
            error_message=str(error),
        )

    if result.status != "success":
        return ToolResult(
            success=False,
            source="nih_reporter",
            data=_build_tool_data(result),
            error_code=_error_code_from_run_result(result),
            error_message=_error_message_from_run_result(result),
            errors=result.errors,
        )

    return ToolResult(
        success=True,
        source="nih_reporter",
        data=_build_tool_data(result),
        errors=result.errors,
    )


SEARCH_FUNDING_TOOL = ToolDefinition(
    name=SEARCH_FUNDING_TOOL_NAME,
    description=SEARCH_FUNDING_DESCRIPTION,
    input_schema=SEARCH_FUNDING_INPUT_SCHEMA,
    effect="external",
    handler=search_funding,
)


def _validate_tool_arguments(arguments: dict[str, Any]) -> NIHReporterSearchParams:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    for field_name in SEARCH_FUNDING_INPUT_SCHEMA["required"]:
        if field_name not in arguments:
            raise ValueError(f"{field_name} is required")

    unexpected_fields = set(arguments) - set(SEARCH_FUNDING_INPUT_SCHEMA["properties"])
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"unexpected argument(s): {names}")

    return validate_nih_reporter_search_inputs(
        pi_name=_optional_string(arguments.get("pi_name"), "pi_name"),
        institution=_optional_string(arguments.get("institution"), "institution"),
        keyword=_optional_string(arguments.get("keyword"), "keyword"),
        from_year=arguments["from_year"],
        to_year=arguments["to_year"],
        max_results=arguments["max_results"],
        raw_dir=Path("data/raw/nih_reporter"),
        processed_dir=Path("data/processed/nih_reporter"),
    )


def _build_tool_data(result: NIHReporterRunResult) -> dict[str, Any]:
    return {
        "source": "nih_reporter",
        "task_id": result.task_id,
        "status": result.status,
        "pi_name": result.search_params.pi_name,
        "institution": result.search_params.institution,
        "keyword": result.search_params.keyword,
        "from_year": result.search_params.from_year,
        "to_year": result.search_params.to_year,
        "max_results": result.search_params.max_results,
        "funding_count": len(result.funding_records),
        "unified_funding_count": len(result.unified_funding),
        "funding_records": [
            _record_to_tool_dict(record) for record in result.funding_records
        ],
        "unified_funding": [
            funding.to_dict() for funding in result.unified_funding
        ],
        "run_report_path": str(result.run_report_path),
        "raw_files": result.raw_files,
        "processed_files": result.processed_files,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "coverage_note": "NIH RePORTER only covers NIH-related funding records.",
        "lead_generation_status": "not_enabled_in_stage21d",
        "official_scoring_status": "not_enabled_in_stage21d",
        "email_status": "not_enabled_in_stage21d",
        "errors": result.errors,
    }


def _record_to_tool_dict(record: NIHFundingRecord) -> dict[str, Any]:
    return {
        "grant_id": record.grant_id,
        "agency": record.agency,
        "project_title": record.project_title,
        "pi_name": record.pi_name,
        "institution": record.institution,
        "fiscal_year": record.fiscal_year,
        "project_start": record.project_start,
        "project_end": record.project_end,
        "amount": record.amount,
        "source_url": record.source_url,
        "raw_record_path": record.raw_record_path,
    }


def _error_code_from_run_result(result: NIHReporterRunResult) -> str:
    stages = {error.get("stage") for error in result.errors}
    if "search" in stages:
        return "nih_reporter_search_failed"
    if "processing" in stages:
        return "nih_reporter_processing_failed"
    return "tool_execution_error"


def _error_message_from_run_result(result: NIHReporterRunResult) -> str:
    if not result.errors:
        return f"NIH RePORTER tool returned status: {result.status}"
    return (
        result.errors[0].get("message")
        or f"NIH RePORTER tool returned status: {result.status}"
    )


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value
