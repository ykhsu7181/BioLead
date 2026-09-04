"""Lead API routes."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.database import fetch_one
from scholarlead_agent.services.lead_list_service import (
    LeadListQuery,
    fetch_lead_filter_options,
    query_leads,
)


router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads")
def list_leads(
    page: int = 1,
    page_size: int = 20,
    lead_ids: str | None = None,
    scope: str = "all",
    task_id: str | None = None,
    query: str | None = None,
    country: str | None = None,
    research: str | None = None,
    email_status: str | None = None,
    contact_status: str | None = None,
    source: str | None = None,
    manual_review: bool | None = None,
    sort_by: str = "last_seen_at",
    sort_dir: str = "desc",
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    requested_ids = _parse_lead_ids(lead_ids)
    for field_name, value, limit in (
        ("query", query, 200),
        ("task_id", task_id, 200),
        ("country", country, 100),
        ("research", research, 100),
        ("source", source, 50),
    ):
        if value is not None and len(value) > limit:
            raise ApiError(
                "INVALID_LEADS_QUERY",
                f"{field_name} must be at most {limit} characters.",
                400,
            )
    try:
        result = query_leads(
            connection,
            LeadListQuery(
                page=page,
                page_size=page_size,
                scope=scope,
                task_id=task_id,
                query=query,
                country=country,
                research=research,
                email_status=email_status,
                contact_status=contact_status,
                source=source,
                manual_review=manual_review,
                sort_by=sort_by,
                sort_dir=sort_dir,
                lead_ids=tuple(requested_ids),
            ),
        )
    except ValueError as error:
        raise ApiError("INVALID_LEADS_QUERY", str(error), 400) from error
    return api_success(result.to_dict())


def _parse_lead_ids(lead_ids: str | None) -> list[str]:
    if not lead_ids:
        return []
    values = [item.strip() for item in lead_ids.split(",") if item.strip()]
    if len(values) > 100:
        raise ApiError("INVALID_LEAD_IDS", "At most 100 lead IDs may be requested.", 400)
    return list(dict.fromkeys(values))


@router.get("/leads/filter-options")
def get_lead_filter_options(
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    return api_success(fetch_lead_filter_options(connection))


@router.get("/leads/{lead_id}")
def get_lead(
    lead_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(connection, "SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
    if row is None:
        raise ApiError("LEAD_NOT_FOUND", "Lead not found", 404)
    return api_success(_lead_row_to_dict(row))


@router.get("/leads/{lead_id}/service-match")
def get_lead_service_match(
    lead_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(connection, "SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
    if row is None:
        raise ApiError("LEAD_NOT_FOUND", "Lead not found", 404)
    payload = json.loads(row["payload_json"] or "{}")
    return api_success(
        payload.get("matched_service")
        or payload.get("service_match")
        or {"lead_id": lead_id, "status": "not_available"}
    )


def _lead_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    payload = json.loads(data.pop("payload_json", "{}") or "{}")
    data["payload"] = payload
    return data
