"""Task API routes."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.database import fetch_all, fetch_one


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}")
def get_task(
    task_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(connection, "SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if row is None:
        raise ApiError("TASK_NOT_FOUND", "Task not found", 404)
    return api_success(_task_row_to_dict(row))


@router.get("/{task_id}/status")
def get_task_status(
    task_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(connection, "SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    if row is None:
        raise ApiError("TASK_NOT_FOUND", "Task not found", 404)
    return api_success(
        {
            "task_id": task_id,
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "run_report_path": row["run_report_path"],
        }
    )


@router.get("/{task_id}/summary")
def get_task_summary(
    task_id: str,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    row = fetch_one(
        connection,
        """
        SELECT
            t.task_id,
            t.query,
            t.status,
            t.started_at,
            t.finished_at,
            COUNT(d.lead_id) AS lead_count
        FROM tasks AS t
        LEFT JOIN lead_discoveries AS d ON d.task_id = t.task_id
        WHERE t.task_id = ?
        GROUP BY t.task_id
        """,
        (task_id,),
    )
    if row is None:
        raise ApiError("TASK_NOT_FOUND", "Task not found", 404)
    row["lead_count"] = int(row["lead_count"])
    return api_success(row)


@router.get("/{task_id}/leads")
def get_task_leads(
    task_id: str,
    page: int = 1,
    page_size: int = 50,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    rows = fetch_all(
        connection,
        """
        SELECT
            l.*,
            d.source,
            d.discovered_at,
            d.discovery_status
        FROM lead_discoveries AS d
        JOIN leads AS l ON l.lead_id = d.lead_id
        WHERE d.task_id = ?
        ORDER BY d.discovered_at DESC, l.lead_id DESC
        """,
        (task_id,),
    )
    items = [dict(row) for row in rows]
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return api_success(
        {"items": items[start:end], "page": page, "page_size": page_size, "total": len(items)}
    )


def _task_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["parameters"] = json.loads(data.pop("parameters_json", "{}") or "{}")
    return data
