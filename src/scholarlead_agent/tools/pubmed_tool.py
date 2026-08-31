"""Agent Tool wrapper for the PubMed first-round service."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.pubmed_models import (
    PUBMED_MAX_RESULTS_LIMIT,
    PubMedLead,
    PubMedPaper,
    PubMedSearchParams,
    validate_pubmed_search_inputs,
)
from scholarlead_agent.services.pubmed_service import PubMedRunResult, run_pubmed_search


SEARCH_PUBMED_TOOL_NAME = "search_pubmed"

SEARCH_PUBMED_DESCRIPTION = (
    "Search real PubMed records and generate PubMed-only candidate research "
    "leads using public PubMed evidence. Use this tool when the user asks for "
    "real papers, authors, public email evidence, PubMed Leads, or temporary "
    "PubMed-only scoring. Results come from PubMed public data. PubMed-only "
    "results do not represent official funding assessment or official "
    "four-dimension scoring. This tool must not be used to send email."
)

SEARCH_PUBMED_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["query", "from_date", "to_date", "max_results"],
    "properties": {
        "query": {
            "type": "string",
            "minLength": 1,
            "description": "PubMed search keywords. Must not be empty.",
        },
        "from_date": {
            "type": "string",
            "format": "date",
            "description": "Publication start date in YYYY-MM-DD format.",
        },
        "to_date": {
            "type": "string",
            "format": "date",
            "description": "Publication end date in YYYY-MM-DD format.",
        },
        "max_results": {
            "type": "integer",
            "minimum": 1,
            "maximum": PUBMED_MAX_RESULTS_LIMIT,
            "description": "Maximum PubMed results to request.",
        },
        "country": {
            "type": "string",
            "description": "Optional target country label.",
        },
        "service_type": {
            "type": "string",
            "description": "Optional service type label, such as scRNA-seq.",
        },
    },
}


PubMedServiceRunner = Callable[[PubMedSearchParams], PubMedRunResult]


def search_pubmed(
    arguments: dict[str, Any],
    *,
    service_runner: PubMedServiceRunner = run_pubmed_search,
) -> ToolResult:
    """Run the PubMed service from structured tool-call arguments."""

    try:
        params = _validate_tool_arguments(arguments)
    except ValueError as error:
        return ToolResult(
            success=False,
            source="pubmed",
            error_code="invalid_arguments",
            error_message=str(error),
        )

    try:
        result = service_runner(params)
    except Exception as error:
        return ToolResult(
            success=False,
            source="pubmed",
            error_code="tool_execution_error",
            error_message=str(error),
        )

    if result.status != "success":
        return ToolResult(
            success=False,
            source="pubmed",
            data=_build_tool_data(result),
            error_code=_error_code_from_run_result(result),
            error_message=_error_message_from_run_result(result),
            errors=result.errors,
        )

    return ToolResult(
        success=True,
        source="pubmed",
        data=_build_tool_data(result),
        errors=result.errors,
        persistence_payload=result,
    )


SEARCH_PUBMED_TOOL = ToolDefinition(
    name=SEARCH_PUBMED_TOOL_NAME,
    description=SEARCH_PUBMED_DESCRIPTION,
    input_schema=SEARCH_PUBMED_INPUT_SCHEMA,
    effect="external",
    handler=search_pubmed,
)


def _validate_tool_arguments(arguments: dict[str, Any]) -> PubMedSearchParams:
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")

    for field_name in SEARCH_PUBMED_INPUT_SCHEMA["required"]:
        if field_name not in arguments:
            raise ValueError(f"{field_name} is required")

    unexpected_fields = set(arguments) - set(SEARCH_PUBMED_INPUT_SCHEMA["properties"])
    if unexpected_fields:
        names = ", ".join(sorted(unexpected_fields))
        raise ValueError(f"unexpected argument(s): {names}")

    max_results = arguments["max_results"]
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer")

    return validate_pubmed_search_inputs(
        query=_require_string(arguments["query"], "query"),
        from_date=_require_string(arguments["from_date"], "from_date"),
        to_date=_require_string(arguments["to_date"], "to_date"),
        max_results=max_results,
        country=_optional_string(arguments.get("country"), "country"),
        service_type=_optional_string(arguments.get("service_type"), "service_type"),
        raw_dir=Path("data/raw/pubmed"),
        processed_dir=Path("data/processed/pubmed"),
    )


def _build_tool_data(result: PubMedRunResult) -> dict[str, Any]:
    return {
        "source": "pubmed",
        "task_id": result.task_id,
        "status": result.status,
        "query": result.search_params.query,
        "from_date": result.search_params.from_date,
        "to_date": result.search_params.to_date,
        "max_results": result.search_params.max_results,
        "paper_count": len(result.papers),
        "lead_count": len(result.leads),
        "papers": [_paper_to_tool_dict(paper) for paper in result.papers],
        "leads": [_lead_to_tool_dict(lead) for lead in result.leads],
        "run_report_path": str(result.run_report_path),
        "raw_files": result.raw_files,
        "processed_files": result.processed_files,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "scoring_mode": result.run_report.get("scoring_mode"),
        "official_scoring_status": "pending_multi_source_data",
        "errors": result.errors,
    }


def _paper_to_tool_dict(paper: PubMedPaper) -> dict[str, Any]:
    return {
        "pmid": paper.pmid,
        "doi": paper.doi,
        "title": paper.title,
        "journal": paper.journal,
        "publication_date": paper.publication_date,
        "publication_year": paper.publication_year,
        "authors": [author.full_name for author in paper.authors],
        "source_url": paper.source_url,
    }


def _lead_to_tool_dict(lead: PubMedLead) -> dict[str, Any]:
    return {
        "lead_id": lead.lead_id,
        "pi_full_name": lead.pi_full_name,
        "verified_email": lead.verified_email,
        "email_status": lead.email_status,
        "email_source_url": lead.email_source_url,
        "name_email_match_confidence": lead.name_email_match_confidence,
        "institution": lead.institution,
        "country": lead.country,
        "country_confidence": lead.country_confidence,
        "country_source": lead.country_source,
        "pmid": lead.pmid,
        "doi": lead.doi,
        "source_links": lead.source_links,
        "matched_keywords": lead.matched_keywords,
        "target_service_type": lead.target_service_type,
        "lead_score": lead.lead_score,
        "priority": lead.priority,
        "score_explanation": lead.score_explanation,
        "data_quality": lead.data_quality,
        "manual_review_required": lead.manual_review_required,
    }


def _error_code_from_run_result(result: PubMedRunResult) -> str:
    stages = {error.get("stage") for error in result.errors}
    if "esearch" in stages:
        return "pubmed_search_failed"
    if "efetch" in stages:
        return "pubmed_fetch_failed"
    if "processing" in stages:
        return "pubmed_processing_failed"
    return "tool_execution_error"


def _error_message_from_run_result(result: PubMedRunResult) -> str:
    if not result.errors:
        return f"PubMed tool returned status: {result.status}"
    return result.errors[0].get("message") or f"PubMed tool returned status: {result.status}"


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value
