"""Minimal background job foundation for ScholarLead Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import sqlite3
from typing import Any, Callable
from uuid import uuid4


JOB_TYPE_BATCH_DRAFT = "BatchDraftJob"
JOB_TYPE_BATCH_SEND = "BatchSendJob"
JOB_TYPE_RESULT_PACKAGE = "ResultPackageJob"

JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELLED = "cancelled"
JOB_STATUS_BLOCKED = "blocked"
JOB_STATUS_INTERRUPTED = "interrupted"
JOB_STATUS_RECOVERABLE = "recoverable"

JOB_ITEM_STATUS_PENDING = "pending"
JOB_ITEM_STATUS_RUNNING = "running"
JOB_ITEM_STATUS_COMPLETED = "completed"
JOB_ITEM_STATUS_FAILED = "failed"
JOB_ITEM_STATUS_BLOCKED = "blocked"
JOB_ITEM_STATUS_SKIPPED = "skipped"
JOB_ITEM_STATUS_NEEDS_REVIEW = "needs_review"

TERMINAL_JOB_STATUSES = {
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_BLOCKED,
}
TERMINAL_ITEM_STATUSES = {
    JOB_ITEM_STATUS_COMPLETED,
    JOB_ITEM_STATUS_FAILED,
    JOB_ITEM_STATUS_BLOCKED,
    JOB_ITEM_STATUS_SKIPPED,
    JOB_ITEM_STATUS_NEEDS_REVIEW,
}
RESUMABLE_ITEM_STATUSES = {
    JOB_ITEM_STATUS_PENDING,
    JOB_ITEM_STATUS_FAILED,
    JOB_ITEM_STATUS_BLOCKED,
    JOB_ITEM_STATUS_NEEDS_REVIEW,
}


@dataclass(frozen=True)
class JobItemSpec:
    """Input specification for one job item."""

    lead_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    job_item_id: str | None = None


@dataclass(frozen=True)
class JobSummary:
    """Persisted job summary."""

    job_id: str
    task_id: str | None
    job_type: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    blocked_count: int
    created_at: str
    started_at: str | None
    finished_at: str | None
    last_error: str | None
    payload: dict[str, Any]
    updated_at: str

    @property
    def progress(self) -> float:
        """Return completion progress from 0.0 to 1.0."""

        if self.total_count <= 0:
            return 1.0 if self.status == JOB_STATUS_COMPLETED else 0.0
        done_count = self.success_count + self.failed_count + self.blocked_count
        return round(min(1.0, done_count / self.total_count), 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "task_id": self.task_id,
            "job_type": self.job_type,
            "status": self.status,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "blocked_count": self.blocked_count,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "last_error": self.last_error,
            "payload": dict(self.payload),
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class JobItem:
    """Persisted job item."""

    job_item_id: str
    job_id: str
    lead_id: str | None
    status: str
    attempt_count: int
    error: str | None
    payload: dict[str, Any]
    created_at: str
    started_at: str | None
    finished_at: str | None
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_item_id": self.job_item_id,
            "job_id": self.job_id,
            "lead_id": self.lead_id,
            "status": self.status,
            "attempt_count": self.attempt_count,
            "error": self.error,
            "payload": dict(self.payload),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "updated_at": self.updated_at,
        }


JobItemHandler = Callable[[JobItem], str | None]


def create_job(
    connection: sqlite3.Connection,
    *,
    job_type: str,
    task_id: str | None = None,
    items: list[JobItemSpec] | None = None,
    payload: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> JobSummary:
    """Create a persisted job and return immediately with its job_id."""

    _validate_job_type(job_type)
    now = _now()
    row_id = job_id or f"job-{uuid4()}"
    item_specs = items or []
    connection.execute(
        """
        INSERT INTO jobs (
            job_id, task_id, job_type, status, total_count, success_count,
            failed_count, blocked_count, created_at, started_at, finished_at,
            last_error, payload_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, NULL, NULL, NULL, ?, ?)
        """,
        (
            row_id,
            task_id,
            job_type,
            JOB_STATUS_PENDING,
            len(item_specs),
            now,
            _json(payload or {}),
            now,
        ),
    )
    for index, item in enumerate(item_specs, start=1):
        item_id = item.job_item_id or f"{row_id}:item-{index}"
        connection.execute(
            """
            INSERT INTO job_items (
                job_item_id, job_id, lead_id, status, attempt_count, error,
                payload_json, created_at, started_at, finished_at, updated_at
            )
            VALUES (?, ?, ?, ?, 0, NULL, ?, ?, NULL, NULL, ?)
            """,
            (
                item_id,
                row_id,
                item.lead_id,
                JOB_ITEM_STATUS_PENDING,
                _json(item.payload),
                now,
                now,
            ),
        )
    connection.commit()
    return fetch_job(connection, row_id)


def fetch_job(connection: sqlite3.Connection, job_id: str) -> JobSummary:
    """Fetch one job summary."""

    row = connection.execute(
        "SELECT * FROM jobs WHERE job_id = ?",
        (job_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"job not found: {job_id}")
    return _job_from_row(row)


def fetch_job_items(connection: sqlite3.Connection, job_id: str) -> list[JobItem]:
    """Fetch items for a job in creation order."""

    rows = connection.execute(
        """
        SELECT * FROM job_items
        WHERE job_id = ?
        ORDER BY created_at, job_item_id
        """,
        (job_id,),
    ).fetchall()
    return [_item_from_row(row) for row in rows]


def start_job(connection: sqlite3.Connection, job_id: str) -> JobSummary:
    """Mark a pending/recoverable job as running."""

    job = fetch_job(connection, job_id)
    if job.status in TERMINAL_JOB_STATUSES:
        return job
    now = _now()
    connection.execute(
        """
        UPDATE jobs
        SET status = ?, started_at = COALESCE(started_at, ?), updated_at = ?
        WHERE job_id = ?
        """,
        (JOB_STATUS_RUNNING, now, now, job_id),
    )
    connection.commit()
    return fetch_job(connection, job_id)


def claim_next_job_item(
    connection: sqlite3.Connection,
    job_id: str,
) -> JobItem | None:
    """Claim the next pending item without touching completed items."""

    job = fetch_job(connection, job_id)
    if job.status in TERMINAL_JOB_STATUSES:
        return None
    row = connection.execute(
        """
        SELECT * FROM job_items
        WHERE job_id = ? AND status = ?
        ORDER BY created_at, job_item_id
        LIMIT 1
        """,
        (job_id, JOB_ITEM_STATUS_PENDING),
    ).fetchone()
    if row is None:
        return None
    item = _item_from_row(row)
    now = _now()
    connection.execute(
        """
        UPDATE job_items
        SET status = ?, attempt_count = attempt_count + 1, started_at = ?,
            error = NULL, updated_at = ?
        WHERE job_item_id = ? AND status = ?
        """,
        (
            JOB_ITEM_STATUS_RUNNING,
            now,
            now,
            item.job_item_id,
            JOB_ITEM_STATUS_PENDING,
        ),
    )
    connection.commit()
    return fetch_job_item(connection, item.job_item_id)


def fetch_job_item(connection: sqlite3.Connection, job_item_id: str) -> JobItem:
    row = connection.execute(
        "SELECT * FROM job_items WHERE job_item_id = ?",
        (job_item_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"job item not found: {job_item_id}")
    return _item_from_row(row)


def complete_job_item(
    connection: sqlite3.Connection,
    job_item_id: str,
    *,
    result_payload: dict[str, Any] | None = None,
) -> JobItem:
    """Mark one running item complete."""

    item = fetch_job_item(connection, job_item_id)
    now = _now()
    payload = dict(item.payload)
    if result_payload:
        payload["result"] = result_payload
    connection.execute(
        """
        UPDATE job_items
        SET status = ?, error = NULL, payload_json = ?, finished_at = ?,
            updated_at = ?
        WHERE job_item_id = ?
        """,
        (
            JOB_ITEM_STATUS_COMPLETED,
            _json(payload),
            now,
            now,
            job_item_id,
        ),
    )
    _refresh_job_counts(connection, item.job_id)
    connection.commit()
    return fetch_job_item(connection, job_item_id)


def fail_job_item(
    connection: sqlite3.Connection,
    job_item_id: str,
    *,
    error: str,
) -> JobItem:
    """Mark one running item failed without failing the whole job."""

    item = fetch_job_item(connection, job_item_id)
    now = _now()
    connection.execute(
        """
        UPDATE job_items
        SET status = ?, error = ?, finished_at = ?, updated_at = ?
        WHERE job_item_id = ?
        """,
        (JOB_ITEM_STATUS_FAILED, error, now, now, job_item_id),
    )
    _refresh_job_counts(connection, item.job_id)
    connection.commit()
    return fetch_job_item(connection, job_item_id)


def block_job_item(
    connection: sqlite3.Connection,
    job_item_id: str,
    *,
    reason: str,
) -> JobItem:
    """Mark one item blocked for permission or policy reasons."""

    item = fetch_job_item(connection, job_item_id)
    now = _now()
    connection.execute(
        """
        UPDATE job_items
        SET status = ?, error = ?, finished_at = ?, updated_at = ?
        WHERE job_item_id = ?
        """,
        (JOB_ITEM_STATUS_BLOCKED, reason, now, now, job_item_id),
    )
    _refresh_job_counts(connection, item.job_id)
    connection.commit()
    return fetch_job_item(connection, job_item_id)


def finalize_job_if_done(connection: sqlite3.Connection, job_id: str) -> JobSummary:
    """Complete or fail a job when all items are terminal."""

    job = fetch_job(connection, job_id)
    if job.status in TERMINAL_JOB_STATUSES:
        return job
    items = fetch_job_items(connection, job_id)
    if not items:
        _set_job_status(connection, job_id, JOB_STATUS_COMPLETED)
        connection.commit()
        return fetch_job(connection, job_id)
    if any(item.status not in TERMINAL_ITEM_STATUSES for item in items):
        return job
    if all(item.status == JOB_ITEM_STATUS_COMPLETED for item in items):
        status = JOB_STATUS_COMPLETED
    elif any(item.status == JOB_ITEM_STATUS_BLOCKED for item in items):
        status = JOB_STATUS_BLOCKED
    else:
        status = JOB_STATUS_FAILED
    _set_job_status(connection, job_id, status)
    connection.commit()
    return fetch_job(connection, job_id)


def recover_interrupted_jobs(connection: sqlite3.Connection) -> list[JobSummary]:
    """Mark orphan running jobs/items as recoverable/interrupted."""

    running_jobs = connection.execute(
        "SELECT * FROM jobs WHERE status = ?",
        (JOB_STATUS_RUNNING,),
    ).fetchall()
    recovered: list[JobSummary] = []
    now = _now()
    for row in running_jobs:
        job_id = str(row["job_id"])
        connection.execute(
            """
            UPDATE job_items
            SET status = ?, error = ?, updated_at = ?
            WHERE job_id = ? AND status = ?
            """,
            (
                JOB_ITEM_STATUS_NEEDS_REVIEW,
                "interrupted while running; manual retry or review required",
                now,
                job_id,
                JOB_ITEM_STATUS_RUNNING,
            ),
        )
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, last_error = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (
                JOB_STATUS_RECOVERABLE,
                "worker missing after restart; running items marked needs_review",
                now,
                job_id,
            ),
        )
        _refresh_job_counts(connection, job_id)
        recovered.append(fetch_job(connection, job_id))
    connection.commit()
    return recovered


def reset_job_item_for_retry(
    connection: sqlite3.Connection,
    job_item_id: str,
) -> JobItem:
    """Reset a non-completed item for manual retry."""

    item = fetch_job_item(connection, job_item_id)
    if item.status == JOB_ITEM_STATUS_COMPLETED:
        return item
    if item.status not in RESUMABLE_ITEM_STATUSES:
        return item
    now = _now()
    connection.execute(
        """
        UPDATE job_items
        SET status = ?, error = NULL, started_at = NULL, finished_at = NULL,
            updated_at = ?
        WHERE job_item_id = ?
        """,
        (JOB_ITEM_STATUS_PENDING, now, job_item_id),
    )
    _set_job_status(connection, item.job_id, JOB_STATUS_RECOVERABLE, finished=False)
    _refresh_job_counts(connection, item.job_id)
    connection.commit()
    return fetch_job_item(connection, job_item_id)


def run_job_once(
    connection: sqlite3.Connection,
    job_id: str,
    *,
    handler: JobItemHandler,
) -> JobSummary:
    """Run pending items synchronously using a provided deterministic handler."""

    start_job(connection, job_id)
    while True:
        item = claim_next_job_item(connection, job_id)
        if item is None:
            break
        try:
            status = handler(item)
        except Exception as error:
            fail_job_item(connection, item.job_item_id, error=str(error))
            continue
        if status == JOB_ITEM_STATUS_BLOCKED:
            block_job_item(connection, item.job_item_id, reason="blocked by handler")
        elif status == JOB_ITEM_STATUS_FAILED:
            fail_job_item(connection, item.job_item_id, error="failed by handler")
        else:
            complete_job_item(connection, item.job_item_id)
    return finalize_job_if_done(connection, job_id)


def _refresh_job_counts(connection: sqlite3.Connection, job_id: str) -> None:
    rows = connection.execute(
        """
        SELECT status, COUNT(*) AS count
        FROM job_items
        WHERE job_id = ?
        GROUP BY status
        """,
        (job_id,),
    ).fetchall()
    counts = {str(row["status"]): int(row["count"]) for row in rows}
    last_error_row = connection.execute(
        """
        SELECT error FROM job_items
        WHERE job_id = ? AND error IS NOT NULL AND error != ''
        ORDER BY updated_at DESC, job_item_id DESC
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    now = _now()
    connection.execute(
        """
        UPDATE jobs
        SET success_count = ?, failed_count = ?, blocked_count = ?,
            last_error = COALESCE(?, last_error), updated_at = ?
        WHERE job_id = ?
        """,
        (
            counts.get(JOB_ITEM_STATUS_COMPLETED, 0),
            counts.get(JOB_ITEM_STATUS_FAILED, 0),
            counts.get(JOB_ITEM_STATUS_BLOCKED, 0),
            last_error_row["error"] if last_error_row is not None else None,
            now,
            job_id,
        ),
    )


def _set_job_status(
    connection: sqlite3.Connection,
    job_id: str,
    status: str,
    *,
    finished: bool = True,
) -> None:
    now = _now()
    connection.execute(
        """
        UPDATE jobs
        SET status = ?, finished_at = CASE WHEN ? THEN ? ELSE finished_at END,
            updated_at = ?
        WHERE job_id = ?
        """,
        (status, int(finished), now, now, job_id),
    )


def _validate_job_type(job_type: str) -> None:
    if job_type not in {
        JOB_TYPE_BATCH_DRAFT,
        JOB_TYPE_BATCH_SEND,
        JOB_TYPE_RESULT_PACKAGE,
    }:
        raise ValueError(f"unsupported job_type: {job_type}")


def _job_from_row(row: sqlite3.Row) -> JobSummary:
    return JobSummary(
        job_id=str(row["job_id"]),
        task_id=row["task_id"],
        job_type=str(row["job_type"]),
        status=str(row["status"]),
        total_count=int(row["total_count"]),
        success_count=int(row["success_count"]),
        failed_count=int(row["failed_count"]),
        blocked_count=int(row["blocked_count"]),
        created_at=str(row["created_at"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        last_error=row["last_error"],
        payload=json.loads(row["payload_json"] or "{}"),
        updated_at=str(row["updated_at"]),
    )


def _item_from_row(row: sqlite3.Row) -> JobItem:
    return JobItem(
        job_item_id=str(row["job_item_id"]),
        job_id=str(row["job_id"]),
        lead_id=row["lead_id"],
        status=str(row["status"]),
        attempt_count=int(row["attempt_count"]),
        error=row["error"],
        payload=json.loads(row["payload_json"] or "{}"),
        created_at=str(row["created_at"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        updated_at=str(row["updated_at"]),
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
