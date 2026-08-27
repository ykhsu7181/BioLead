"""PubMed search API routes."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.pubmed import PubMedSearchRequest
from scholarlead_agent.database import persist_pubmed_run_result
from scholarlead_agent.pubmed_models import validate_pubmed_search_inputs
from scholarlead_agent.services.pubmed_service import run_pubmed_search


router = APIRouter(prefix="/api/pubmed", tags=["pubmed"])


@router.post("/search")
def search_pubmed(
    request: PubMedSearchRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    """Run a real PubMed search through the existing service and persist results."""

    try:
        params = validate_pubmed_search_inputs(
            query=request.query,
            from_date=request.from_date,
            to_date=request.to_date,
            max_results=request.max_results,
            country=request.country,
            service_type=request.service_type,
            raw_dir=request.raw_dir,
            processed_dir=request.processed_dir,
        )
    except ValueError as error:
        raise ApiError("INVALID_PUBMED_SEARCH_REQUEST", str(error), 400) from error

    result = run_pubmed_search(params)
    persist_pubmed_run_result(connection, result)
    return api_success(_pubmed_result_to_dict(result))


def _pubmed_result_to_dict(result: Any) -> dict[str, Any]:
    return {
        "task_id": result.task_id,
        "status": result.status,
        "query": result.search_params.query,
        "from_date": result.search_params.from_date,
        "to_date": result.search_params.to_date,
        "max_results": result.search_params.max_results,
        "pmids": list(result.pmids),
        "papers": [_to_dict(paper) for paper in result.papers],
        "leads": [_to_dict(lead) for lead in result.leads],
        "raw_files": dict(result.raw_files),
        "processed_files": dict(result.processed_files),
        "run_report_path": str(result.run_report_path),
        "run_report": dict(result.run_report),
        "errors": list(result.errors),
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def _to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, dict):
        return dict(value)
    return dict(value)
