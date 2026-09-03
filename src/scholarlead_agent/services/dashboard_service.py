"""Database-backed summary data for the BioLead dashboard."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import sqlite3
from typing import Any

from scholarlead_agent.services.email_business_status import (
    EMAIL_STATUS_PENDING_REVIEW,
    EMAIL_STATUS_READY_TO_SEND,
    summarize_email_business_statuses,
)


@dataclass(frozen=True)
class RecentTaskSummary:
    task_id: str
    query: str | None
    status: str
    started_at: str | None
    finished_at: str | None
    lead_count: int


@dataclass(frozen=True)
class DashboardSummary:
    lead_count: int
    pending_review_count: int
    ready_to_send_count: int
    manual_review_lead_count: int
    recent_tasks: list[RecentTaskSummary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_count": self.lead_count,
            "pending_review_count": self.pending_review_count,
            "ready_to_send_count": self.ready_to_send_count,
            "manual_review_lead_count": self.manual_review_lead_count,
            "recent_tasks": [asdict(task) for task in self.recent_tasks],
        }


def get_dashboard_summary(
    connection: sqlite3.Connection,
    *,
    recent_task_limit: int = 5,
) -> DashboardSummary:
    """Build one dashboard response from current persisted project data."""

    if isinstance(recent_task_limit, bool) or recent_task_limit < 1:
        raise ValueError("recent_task_limit must be a positive integer")

    lead_count = _scalar_count(connection, "SELECT COUNT(*) FROM leads")
    manual_review_lead_count = _scalar_count(
        connection,
        "SELECT COUNT(*) FROM leads WHERE manual_review_required = 1",
    )
    email_counts = summarize_email_business_statuses(connection)
    task_rows = connection.execute(
        """
        SELECT
            t.task_id,
            t.query,
            t.status,
            t.started_at,
            t.finished_at,
            (
                SELECT COUNT(*)
                FROM leads AS l
                WHERE l.task_id = t.task_id
            ) AS lead_count
        FROM tasks AS t
        ORDER BY COALESCE(t.updated_at, t.created_at) DESC, t.task_id DESC
        LIMIT ?
        """,
        (recent_task_limit,),
    ).fetchall()
    recent_tasks = [
        RecentTaskSummary(
            task_id=str(row["task_id"]),
            query=row["query"],
            status=str(row["status"]),
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            lead_count=int(row["lead_count"]),
        )
        for row in task_rows
    ]
    return DashboardSummary(
        lead_count=lead_count,
        pending_review_count=email_counts[EMAIL_STATUS_PENDING_REVIEW],
        ready_to_send_count=email_counts[EMAIL_STATUS_READY_TO_SEND],
        manual_review_lead_count=manual_review_lead_count,
        recent_tasks=recent_tasks,
    )


def _scalar_count(connection: sqlite3.Connection, query: str) -> int:
    row = connection.execute(query).fetchone()
    return int(row[0] if row is not None else 0)
