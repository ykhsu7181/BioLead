from pathlib import Path

import pytest

from scholarlead_agent.database import (
    initialize_database,
    insert_email_draft,
    insert_task,
    record_lead_discovery,
)
from scholarlead_agent.services.dashboard_service import get_dashboard_summary


def test_dashboard_summary_uses_real_counts_and_latest_five_tasks(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "dashboard.sqlite") as connection:
        for index in range(7):
            task_id = f"task-{index}"
            insert_task(
                connection,
                task_id=task_id,
                task_type="pubmed_search",
                query=f"query {index}",
                status="success",
                started_at=f"2026-09-03T10:0{index}:00",
                finished_at=f"2026-09-03T10:0{index}:30",
            )
            connection.execute(
                "UPDATE tasks SET created_at = ?, updated_at = ? WHERE task_id = ?",
                (f"2026-09-03T10:0{index}:00", f"2026-09-03T10:0{index}:30", task_id),
            )

        for lead_id, task_id, manual_review in [
            ("lead-1", "task-6", 1),
            ("lead-2", "task-6", 0),
            ("lead-3", "task-5", 1),
        ]:
            connection.execute(
                """
                INSERT INTO leads (
                    lead_id, task_id, pi_full_name, manual_review_required,
                    payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, '{}', ?, ?)
                """,
                (
                    lead_id,
                    task_id,
                    f"PI {lead_id}",
                    manual_review,
                    "2026-09-03T10:00:00",
                    "2026-09-03T10:00:00",
                ),
            )
            record_lead_discovery(
                connection,
                task_id=task_id,
                lead_id=lead_id,
                source="pubmed",
                discovered_at="2026-09-03T10:00:00",
                discovery_status="new_record",
            )
        insert_email_draft(connection, {"draft_status": "review_pending"}, draft_id="pending")
        insert_email_draft(connection, {"draft_status": "changes_requested"}, draft_id="changes")
        insert_email_draft(connection, {"draft_status": "review_approved"}, draft_id="ready")
        connection.commit()

        summary = get_dashboard_summary(connection)

    assert summary.lead_count == 3
    assert summary.manual_review_lead_count == 2
    assert summary.pending_review_count == 2
    assert summary.ready_to_send_count == 1
    assert len(summary.recent_tasks) == 5
    assert summary.recent_tasks[0].task_id == "task-6"
    assert summary.recent_tasks[0].lead_count == 2
    assert summary.recent_tasks[1].task_id == "task-5"
    assert summary.recent_tasks[1].lead_count == 1


def test_dashboard_historical_count_survives_latest_task_pointer_change(
    tmp_path: Path,
) -> None:
    with initialize_database(tmp_path / "dashboard.sqlite") as connection:
        for task_id in ("task-a", "task-b"):
            insert_task(
                connection,
                task_id=task_id,
                task_type="pubmed_search",
                status="success",
            )
        connection.execute(
            """
            INSERT INTO leads (
                lead_id, task_id, pi_full_name, payload_json, created_at, updated_at
            ) VALUES ('lead-x', 'task-b', 'PI X', '{}', ?, ?)
            """,
            ("2026-09-03T10:00:00", "2026-09-03T10:00:00"),
        )
        for task_id, status in (("task-a", "new_record"), ("task-b", "repeat_record")):
            record_lead_discovery(
                connection,
                task_id=task_id,
                lead_id="lead-x",
                source="pubmed",
                discovered_at=f"2026-09-03T10:0{1 if task_id == 'task-a' else 2}:00",
                discovery_status=status,
            )

        summary = get_dashboard_summary(connection)
        counts = {task.task_id: task.lead_count for task in summary.recent_tasks}

    assert counts["task-a"] == 1
    assert counts["task-b"] == 1


def test_dashboard_summary_rejects_invalid_recent_task_limit(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "dashboard.sqlite") as connection:
        with pytest.raises(ValueError, match="positive integer"):
            get_dashboard_summary(connection, recent_task_limit=0)
        with pytest.raises(ValueError, match="positive integer"):
            get_dashboard_summary(connection, recent_task_limit=True)
