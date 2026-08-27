"""Job API routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.job import CreateJobRequest, RetryJobRequest
from scholarlead_agent.background_jobs import (
    JobItemSpec,
    create_job,
    fetch_job,
    fetch_job_items,
    reset_job_item_for_retry,
)


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("")
def create_background_job(
    request: CreateJobRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        job = create_job(
            connection,
            job_type=request.job_type,
            task_id=request.task_id,
            payload=dict(request.payload),
            items=[
                JobItemSpec(lead_id=item.lead_id, payload=dict(item.payload))
                for item in request.items
            ],
        )
    except ValueError as error:
        raise ApiError("INVALID_JOB_REQUEST", str(error), 400) from error
    return api_success(job.to_dict())


@router.get("/{job_id}")
def get_job(
    job_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        return api_success(fetch_job(connection, job_id).to_dict())
    except ValueError as error:
        raise ApiError("JOB_NOT_FOUND", str(error), 404) from error


@router.get("/{job_id}/items")
def get_job_items(
    job_id: str,
    page: int = 1,
    page_size: int = 50,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        fetch_job(connection, job_id)
    except ValueError as error:
        raise ApiError("JOB_NOT_FOUND", str(error), 404) from error
    items = [item.to_dict() for item in fetch_job_items(connection, job_id)]
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return api_success(
        {
            "items": items[start:end],
            "page": page,
            "page_size": page_size,
            "total": len(items),
        }
    )


@router.post("/{job_id}/retry")
def retry_job_item(
    job_id: str,
    request: RetryJobRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        fetch_job(connection, job_id)
        item = reset_job_item_for_retry(connection, request.job_item_id)
    except ValueError as error:
        raise ApiError("JOB_ITEM_NOT_FOUND", str(error), 404) from error
    if item.job_id != job_id:
        raise ApiError("JOB_ITEM_NOT_FOUND", "Job item does not belong to job", 404)
    return api_success(item.to_dict())
