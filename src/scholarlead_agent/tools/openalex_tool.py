"""Agent Tool wrapper for the OpenAlex service."""

from __future__ import annotations

from typing import Any, Callable

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.services.openalex_service import (
    OpenAlexRunResult,
    run_openalex_search,
)
from scholarlead_agent.works import MAX_RESULTS_LIMIT, PaperRecord, SearchParams, validate_search_inputs


SEARCH_OPENALEX_TOOL_NAME = "search_openalex"

SEARCH_OPENALEX_DESCRIPTION = (
    "Search OpenAlex Works metadata for papers, DOI completion, authorship, "
    "institution, abstract, and publication metadata. Use this tool for open "
    "literature graph enrichment. It does not generate leads, does not score "
    "leads, and must not be used to send email."
)

SEARCH_OPENALEX_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["query", "from_date", "to_date", "max_results"],
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "from_date": {"type": "string", "format": "date"},
        "to_date": {"type": "string", "format": "date"},
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_RESULTS_LIMIT,
        },
    },
}


OpenAlexServiceRunner = Callable[[SearchParams], OpenAlexRunResult]


def search_openalex(
    arguments: dict[str, Any],
    *,
    service_runner: OpenAlexServiceRunner = run_openalex_search,
) -> ToolResult:
    """Run the OpenAlex service from structured tool-call arguments."""

    try:
        params = _validate_tool_arguments(arguments)
    except ValueError as error:
        return ToolResult(
            success=False,
            source="openalex",
            error_code="invalid_arguments",
            error_message=str(error),
        )

    try:
        result = service_runner(params)
    except Exception as error:
        return ToolResult(
            success=False,
            source="openalex",
            error_code="tool_execution_error",
            error_message=str(error),
        )

    if result.status != "success":
        return ToolResult(
            success=False,
            source="openalex",
            data=_build_tool_data(result),
            error_code=_error_code_from_run_result(result),
            error_message=_error_message_from_run_result(result),
            errors=result.errors,
        )

    return ToolResult(
        success=True,
        source="openalex",
        data=_build_tool_data(result),
        errors=result.errors,
    )


SEARCH_OPENALEX_TOOL = ToolDefinition(
    name=SEARCH_OPENALEX_TOOL_NAME,
    description=SEARCH_OPENALEX_DESCRIPTION,
    input_schema=SEARCH_OPENALEX_INPUT_SCHEMA,
    effect="external",
    handler=search_openalex,
)


def _validate_tool_arguments(arguments: dict[str, Any]) -> SearchParams:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    for field_name in SEARCH_OPENALEX_INPUT_SCHEMA["required"]:
        if field_name not in arguments:
            raise ValueError(f"{field_name} is required")

    unexpected_fields = set(arguments) - set(SEARCH_OPENALEX_INPUT_SCHEMA["properties"])
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"unexpected argument(s): {names}")

    max_results = arguments["max_results"]
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer")

    return validate_search_inputs(
        _require_string(arguments["query"], "query"),
        _require_string(arguments["from_date"], "from_date"),
        _require_string(arguments["to_date"], "to_date"),
        max_results,
    )


def _build_tool_data(result: OpenAlexRunResult) -> dict[str, Any]:
    return {
        "source": "openalex",
        "task_id": result.task_id,
        "status": result.status,
        "query": result.search_params.query,
        "from_date": result.search_params.from_date,
        "to_date": result.search_params.to_date,
        "max_results": result.search_params.max_results,
        "work_count": len(result.works),
        "unified_paper_count": len(result.unified_papers),
        "works": [_work_to_tool_dict(work) for work in result.works],
        "unified_papers": [
            paper.to_dict() for paper in result.unified_papers
        ],
        "run_report_path": str(result.run_report_path),
        "raw_files": result.raw_files,
        "processed_files": result.processed_files,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "lead_generation_status": "not_enabled_in_stage21c",
        "scoring_status": "not_enabled_in_stage21c",
        "email_status": "not_enabled_in_stage21c",
        "errors": result.errors,
    }


def _work_to_tool_dict(work: PaperRecord) -> dict[str, Any]:
    return {
        "openalex_id": work.openalex_id,
        "doi": work.doi,
        "title": work.title,
        "abstract": work.abstract,
        "publication_date": work.publication_date,
        "authors": work.authors,
        "institutions": work.institutions,
    }


def _error_code_from_run_result(result: OpenAlexRunResult) -> str:
    stages = {error.get("stage") for error in result.errors}
    if "fetch" in stages:
        return "openalex_fetch_failed"
    if "processing" in stages:
        return "openalex_processing_failed"
    return "tool_execution_error"


def _error_message_from_run_result(result: OpenAlexRunResult) -> str:
    if not result.errors:
        return f"OpenAlex tool returned status: {result.status}"
    return (
        result.errors[0].get("message")
        or f"OpenAlex tool returned status: {result.status}"
    )


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value
