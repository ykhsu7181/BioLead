"""Lead API routes."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.database import fetch_all, fetch_one


router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads")
def list_leads(
    page: int = 1,
    page_size: int = 50,
    lead_ids: str | None = None,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    requested_ids = _parse_lead_ids(lead_ids)
    if requested_ids:
        placeholders = ", ".join("?" for _ in requested_ids)
        rows_by_id = {
            str(row["lead_id"]): row
            for row in fetch_all(
                connection,
                f"SELECT * FROM leads WHERE lead_id IN ({placeholders})",
                tuple(requested_ids),
            )
        }
        rows = [rows_by_id[lead_id] for lead_id in requested_ids if lead_id in rows_by_id]
    else:
        rows = fetch_all(
            connection,
            "SELECT * FROM leads ORDER BY updated_at DESC, lead_id DESC",
        )
    items = [_lead_row_to_dict(row) for row in rows]
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


def _parse_lead_ids(lead_ids: str | None) -> list[str]:
    if not lead_ids:
        return []
    values = [item.strip() for item in lead_ids.split(",") if item.strip()]
    if len(values) > 100:
        raise ApiError("INVALID_LEAD_IDS", "At most 100 lead IDs may be requested.", 400)
    return list(dict.fromkeys(values))


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
