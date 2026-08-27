"""Agent Tool wrapper for the Crossref service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.crossref_models import (
    CROSSREF_MAX_RESULTS_LIMIT,
    CrossrefSearchParams,
    CrossrefWork,
    validate_crossref_search_inputs,
)
from scholarlead_agent.services.crossref_service import (
    CrossrefRunResult,
    run_crossref_search,
)


SEARCH_CROSSREF_TOOL_NAME = "search_crossref"

SEARCH_CROSSREF_DESCRIPTION = (
    "Search Crossref Works metadata by DOI or title. Use this tool to supplement "
    "DOI, title, author, journal, publisher, publication date, citation-count, "
    "and explicit Crossref funder metadata. This tool does not generate leads, "
    "does not score leads, and must not be used to send email or infer active "
    "funding."
)

SEARCH_CROSSREF_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["max_results"],
    "properties": {
        "doi": {
            "type": "string",
            "description": "Optional DOI. If present, DOI lookup is used.",
        },
        "title": {
            "type": "string",
            "description": "Optional title query used when DOI is not provided.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": CROSSREF_MAX_RESULTS_LIMIT,
            "description": "Maximum Crossref results for title search.",
        },
    },
}


CrossrefServiceRunner = Callable[[CrossrefSearchParams], CrossrefRunResult]


def search_crossref(
    arguments: dict[str, Any],
    *,
    service_runner: CrossrefServiceRunner = run_crossref_search,
) -> ToolResult:
    """Run the Crossref service from structured tool-call arguments."""

    try:
        params = _validate_tool_arguments(arguments)
    except ValueError as error:
        return ToolResult(
            success=False,
            source="crossref",
            error_code="invalid_arguments",
            error_message=str(error),
        )

    try:
        result = service_runner(params)
    except Exception as error:
        return ToolResult(
            success=False,
            source="crossref",
            error_code="tool_execution_error",
            error_message=str(error),
        )

    if result.status != "success":
        return ToolResult(
            success=False,
            source="crossref",
            data=_build_tool_data(result),
            error_code=_error_code_from_run_result(result),
            error_message=_error_message_from_run_result(result),
            errors=result.errors,
        )

    return ToolResult(
        success=True,
        source="crossref",
        data=_build_tool_data(result),
        errors=result.errors,
    )


SEARCH_CROSSREF_TOOL = ToolDefinition(
    name=SEARCH_CROSSREF_TOOL_NAME,
    description=SEARCH_CROSSREF_DESCRIPTION,
    input_schema=SEARCH_CROSSREF_INPUT_SCHEMA,
    effect="external",
    handler=search_crossref,
)


def _validate_tool_arguments(arguments: dict[str, Any]) -> CrossrefSearchParams:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")

    unexpected_fields = set(arguments) - set(SEARCH_CROSSREF_INPUT_SCHEMA["properties"])
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"unexpected argument(s): {names}")
    if "max_results" not in arguments:
        raise ValueError("max_results is required")

    return validate_crossref_search_inputs(
        doi=_optional_string(arguments.get("doi"), "doi"),
        title=_optional_string(arguments.get("title"), "title"),
        max_results=arguments["max_results"],
        raw_dir=Path("data/raw/crossref"),
        processed_dir=Path("data/processed/crossref"),
    )


def _build_tool_data(result: CrossrefRunResult) -> dict[str, Any]:
    return {
        "source": "crossref",
        "task_id": result.task_id,
        "status": result.status,
        "doi": result.search_params.doi,
        "title": result.search_params.title,
        "max_results": result.search_params.max_results,
        "work_count": len(result.works),
        "works": [_work_to_tool_dict(work) for work in result.works],
        "run_report_path": str(result.run_report_path),
        "raw_files": result.raw_files,
        "processed_files": result.processed_files,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "lead_generation_status": "not_enabled_in_stage21a",
        "scoring_status": "not_enabled_in_stage21a",
        "email_status": "not_enabled_in_stage21a",
        "errors": result.errors,
    }


def _work_to_tool_dict(work: CrossrefWork) -> dict[str, Any]:
    return {
        "crossref_id": work.crossref_id,
        "doi": work.doi,
        "title": work.title,
        "journal": work.journal,
        "publisher": work.publisher,
        "publication_date": work.publication_date,
        "publication_year": work.publication_year,
        "authors": work.authors,
        "funder_names": work.funder_names,
        "reference_count": work.reference_count,
        "is_referenced_by_count": work.is_referenced_by_count,
        "source_url": work.source_url,
    }


def _error_code_from_run_result(result: CrossrefRunResult) -> str:
    stages = {error.get("stage") for error in result.errors}
    if "search" in stages:
        return "crossref_search_failed"
    if "processing" in stages:
        return "crossref_processing_failed"
    return "tool_execution_error"


def _error_message_from_run_result(result: CrossrefRunResult) -> str:
    if not result.errors:
        return f"Crossref tool returned status: {result.status}"
    return (
        result.errors[0].get("message")
        or f"Crossref tool returned status: {result.status}"
    )


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value
