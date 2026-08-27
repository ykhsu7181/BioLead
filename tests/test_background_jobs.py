from scholarlead_agent.background_jobs import (
    JOB_ITEM_STATUS_COMPLETED,
    JOB_ITEM_STATUS_FAILED,
    JOB_ITEM_STATUS_NEEDS_REVIEW,
    JOB_ITEM_STATUS_PENDING,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_FAILED,
    JOB_STATUS_RECOVERABLE,
    JOB_STATUS_RUNNING,
    JOB_TYPE_BATCH_DRAFT,
    JOB_TYPE_RESULT_PACKAGE,
    JobItemSpec,
    claim_next_job_item,
    complete_job_item,
    create_job,
    fail_job_item,
    fetch_job,
    fetch_job_items,
    recover_interrupted_jobs,
    reset_job_item_for_retry,
    run_job_once,
    start_job,
)
from scholarlead_agent.database import initialize_database, list_tables


def test_create_job_returns_immediately_and_persists_items() -> None:
    with initialize_database(":memory:") as connection:
        job = create_job(
            connection,
            job_type=JOB_TYPE_BATCH_DRAFT,
            task_id="task-1",
            items=[
                JobItemSpec(lead_id="lead-1", payload={"index": 1}),
                JobItemSpec(lead_id="lead-2", payload={"index": 2}),
            ],
            payload={"note": "demo"},
            job_id="job-1",
        )
        items = fetch_job_items(connection, "job-1")

    assert job.job_id == "job-1"
    assert job.status == "pending"
    assert job.total_count == 2
    assert job.progress == 0
    assert job.payload == {"note": "demo"}
    assert [item.lead_id for item in items] == ["lead-1", "lead-2"]
    assert all(item.status == JOB_ITEM_STATUS_PENDING for item in items)


def test_run_job_once_completes_items_and_updates_progress() -> None:
    calls: list[str] = []
    with initialize_database(":memory:") as connection:
        create_job(
            connection,
            job_type=JOB_TYPE_RESULT_PACKAGE,
            items=[
                JobItemSpec(lead_id="lead-1"),
                JobItemSpec(lead_id="lead-2"),
            ],
            job_id="job-2",
        )

        job = run_job_once(
            connection,
            "job-2",
            handler=lambda item: calls.append(item.job_item_id) or None,
        )
        items = fetch_job_items(connection, "job-2")

    assert job.status == JOB_STATUS_COMPLETED
    assert job.success_count == 2
    assert job.failed_count == 0
    assert job.progress == 1
    assert len(calls) == 2
    assert all(item.status == JOB_ITEM_STATUS_COMPLETED for item in items)
    assert all(item.attempt_count == 1 for item in items)


def test_single_item_failure_does_not_stop_whole_job() -> None:
    with initialize_database(":memory:") as connection:
        create_job(
            connection,
            job_type=JOB_TYPE_BATCH_DRAFT,
            items=[
                JobItemSpec(lead_id="lead-1"),
                JobItemSpec(lead_id="lead-2"),
            ],
            job_id="job-3",
        )

        job = run_job_once(
            connection,
            "job-3",
            handler=lambda item: (
                (_ for _ in ()).throw(RuntimeError("boom"))
                if item.lead_id == "lead-1"
                else None
            ),
        )
        items = fetch_job_items(connection, "job-3")

    assert job.status == JOB_STATUS_FAILED
    assert job.success_count == 1
    assert job.failed_count == 1
    assert job.last_error == "boom"
    assert sorted(item.status for item in items) == [
        JOB_ITEM_STATUS_COMPLETED,
        JOB_ITEM_STATUS_FAILED,
    ]


def test_completed_items_are_not_rerun_after_manual_retry() -> None:
    calls: list[str] = []
    with initialize_database(":memory:") as connection:
        create_job(
            connection,
            job_type=JOB_TYPE_BATCH_DRAFT,
            items=[
                JobItemSpec(lead_id="lead-1"),
                JobItemSpec(lead_id="lead-2"),
            ],
            job_id="job-4",
        )
        start_job(connection, "job-4")
        first = claim_next_job_item(connection, "job-4")
        assert first is not None
        complete_job_item(connection, first.job_item_id)
        second = claim_next_job_item(connection, "job-4")
        assert second is not None
        fail_job_item(connection, second.job_item_id, error="temporary")
        reset_job_item_for_retry(connection, second.job_item_id)

        job = run_job_once(
            connection,
            "job-4",
            handler=lambda item: calls.append(item.job_item_id) or None,
        )
        items = fetch_job_items(connection, "job-4")

    assert job.status == JOB_STATUS_COMPLETED
    assert calls == [second.job_item_id]
    assert all(item.status == JOB_ITEM_STATUS_COMPLETED for item in items)
    assert [item.attempt_count for item in items] == [1, 2]


def test_recover_interrupted_jobs_marks_running_items_needs_review() -> None:
    with initialize_database(":memory:") as connection:
        create_job(
            connection,
            job_type=JOB_TYPE_BATCH_DRAFT,
            items=[JobItemSpec(lead_id="lead-1")],
            job_id="job-5",
        )
        start_job(connection, "job-5")
        item = claim_next_job_item(connection, "job-5")
        assert item is not None

        recovered = recover_interrupted_jobs(connection)
        job = fetch_job(connection, "job-5")
        items = fetch_job_items(connection, "job-5")

    assert [item.job_id for item in recovered] == ["job-5"]
    assert job.status == JOB_STATUS_RECOVERABLE
    assert items[0].status == JOB_ITEM_STATUS_NEEDS_REVIEW
    assert "interrupted" in (items[0].error or "")


def test_job_tables_are_created_by_database_schema() -> None:
    with initialize_database(":memory:") as connection:
        tables = list_tables(connection)

    assert "jobs" in tables
    assert "job_items" in tables
