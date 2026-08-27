# PubMed Stage 34: Background Job Foundation

## Scope

Stage 34 adds a minimal local background job foundation.

It does not implement:

- FastAPI
- Vue
- Redis / Celery / RQ
- batch email drafting
- batch email sending
- unattended send retry

## Job Types

The first version defines:

```text
BatchDraftJob
BatchSendJob
ResultPackageJob
```

These are job metadata types only. Stage 34 does not implement real batch drafting or sending logic.

## Status

Job status:

```text
pending
running
completed
failed
cancelled
blocked
interrupted
recoverable
```

Job item status:

```text
pending
running
completed
failed
blocked
skipped
needs_review
```

## Database Tables

Stage 34 adds:

```text
jobs
job_items
```

`task_id` and `lead_id` are stored as weak references. They do not require the target task or lead row to already exist, because the first version may create job metadata before all normalized rows are inserted.

## Service

Implemented in:

```text
src/scholarlead_agent/background_jobs.py
```

Main functions:

- `create_job`
- `fetch_job`
- `fetch_job_items`
- `start_job`
- `claim_next_job_item`
- `complete_job_item`
- `fail_job_item`
- `block_job_item`
- `finalize_job_if_done`
- `recover_interrupted_jobs`
- `reset_job_item_for_retry`
- `run_job_once`

## Recovery Boundary

If a job is `running` but no worker is active after restart:

- job becomes `recoverable`
- running job items become `needs_review`
- completed items remain completed

Completed items are not rerun. Non-completed items may be manually reset for retry.

## Validation

Related tests:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_background_jobs.py tests\test_database.py tests\test_database_main.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
