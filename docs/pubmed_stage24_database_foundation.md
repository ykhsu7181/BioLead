# Stage 24: Database And Product Foundation

## Goal

Stage 24 adds a minimal SQLite foundation for later product workflows.

This stage does not replace raw data preservation or JSON / CSV exports. The
existing file outputs remain the source of auditability for collection runs.

## Implemented

- SQLite schema initialization.
- Schema version tracking with `PRAGMA user_version`.
- Minimal database CLI.
- Database path configuration.
- Insert helpers for current core objects.
- Regression tests for schema and inserts.

## Database Path

Default path:

```text
data/processed/scholarlead_agent.sqlite
```

Environment variable:

```text
DATABASE_PATH=data/processed/scholarlead_agent.sqlite
```

The path is under `data/processed`, so generated database files are ignored by
Git through the existing data ignore rules.

## Initialize Database

PowerShell:

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m scholarlead_agent.database_main --show-tables
```

Custom path:

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.database_main `
  --database-path data\processed\scholarlead_agent.sqlite `
  --show-tables
```

After editable install, the script entry point is:

```powershell
scholarlead-db --show-tables
```

## Tables

Stage 24 creates these tables:

- `schema_migrations`
- `tasks`
- `papers`
- `researchers`
- `organizations`
- `contacts`
- `funding_records`
- `leads`
- `evidence_records`
- `email_drafts`
- `email_reviews`
- `email_send_logs`
- `ai_usage`
- `tool_calls`
- `run_reports`
- `settings`

## Insert Helpers

`src/scholarlead_agent/database.py` provides:

- `initialize_database`
- `connect_database`
- `get_schema_version`
- `list_tables`
- `insert_task`
- `insert_pubmed_paper`
- `insert_pubmed_lead`
- `persist_pubmed_run_result`
- `insert_evidence_record`
- `insert_email_draft`
- `insert_email_review_record`
- `insert_email_send_log`
- `insert_ai_usage_record`
- `insert_tool_call`
- `insert_run_report`
- `fetch_one`
- `fetch_all`

The insert helpers store important searchable columns directly and keep full
source payloads as JSON text where useful.

## Boundaries

This stage does not add:

- production backend;
- login or roles;
- database-backed Streamlit workspace;
- automatic migration framework beyond schema version 1;
- real email sending;
- replacement of raw / processed files;
- ORM dependency.

## Tests

Targeted tests:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_database.py tests\test_database_main.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
