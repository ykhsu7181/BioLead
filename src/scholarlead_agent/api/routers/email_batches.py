"""Batch email draft, review, and send API routes."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.email_batch import (
    BatchDraftRequest,
    BatchReviewRequest,
    BatchSendRequest,
)
from scholarlead_agent.database import fetch_all, fetch_one
from scholarlead_agent.services.email_batch_service import (
    apply_batch_email_review,
    generate_batch_email_drafts,
    send_batch_reviewed_emails,
)
from scholarlead_agent.services.email_reviewer_workspace import (
    build_email_reviewer_workspace,
)


router = APIRouter(prefix="/api", tags=["email-batches"])


@router.get("/email-drafts")
def list_email_drafts(
    page: int = 1,
    page_size: int = 50,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    rows = fetch_all(
        connection,
        "SELECT * FROM email_drafts ORDER BY updated_at DESC, draft_id DESC",
    )
    items = [_draft_row_to_dict(row) for row in rows]
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return api_success({"items": items[start:end], "page": page, "page_size": page_size, "total": len(items)})


@router.get("/email-drafts/{draft_id}")
def get_email_draft(
    draft_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(connection, "SELECT * FROM email_drafts WHERE draft_id = ?", (draft_id,))
    if row is None:
        raise ApiError("EMAIL_DRAFT_NOT_FOUND", "Email draft not found", 404)
    return api_success(_draft_row_to_dict(row))


@router.post("/email-drafts/batch-generate")
def batch_generate_email_drafts(
    request: BatchDraftRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        result = generate_batch_email_drafts(
            connection,
            lead_ids=request.lead_ids or None,
            task_id=request.task_id,
            max_items=request.max_items,
        )
    except ValueError as error:
        raise ApiError("INVALID_BATCH_DRAFT_REQUEST", str(error), 400) from error
    return api_success(result.to_dict())


@router.post("/email-drafts/batch-review")
def batch_review_email_drafts(
    request: BatchReviewRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        result = apply_batch_email_review(
            connection,
            draft_ids=request.draft_ids,
            reviewer=request.reviewer,
            decision=request.decision,
            comments=request.comments,
        )
    except ValueError as error:
        raise ApiError("INVALID_BATCH_REVIEW_REQUEST", str(error), 400) from error
    return api_success(result.to_dict())


@router.post("/email-sends/batch-send")
def batch_send_email_drafts(
    request: BatchSendRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    try:
        result = send_batch_reviewed_emails(
            connection,
            draft_ids=request.draft_ids,
            actor=request.actor,
            mode=request.mode,
            max_items=request.max_items,
        )
    except ValueError as error:
        raise ApiError("INVALID_BATCH_SEND_REQUEST", str(error), 400) from error
    return api_success(result.to_dict())


@router.get("/email-sends")
def list_email_send_logs(
    page: int = 1,
    page_size: int = 50,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    rows = fetch_all(
        connection,
        "SELECT * FROM email_send_logs ORDER BY attempted_at DESC, send_id DESC",
    )
    items = [_send_row_to_dict(row) for row in rows]
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return api_success({"items": items[start:end], "page": page, "page_size": page_size, "total": len(items)})


def _draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    payload = json.loads(data.pop("payload_json", "{}") or "{}")
    data["payload"] = payload
    data["reviewer_workspace"] = build_email_reviewer_workspace({**payload, **data})
    return data


def _send_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["permission_blockers"] = json.loads(data.pop("permission_blockers_json", "[]") or "[]")
    data["permission_warnings"] = json.loads(data.pop("permission_warnings_json", "[]") or "[]")
    data["payload"] = json.loads(data.pop("payload_json", "{}") or "{}")
    return data
