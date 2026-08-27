# PubMed Stage 37: Result Package v2 And Closed Loop

## Goal

Stage 37 upgrades the final delivery package so the project can export the full
first-round workflow result:

```text
PubMed task
-> papers
-> leads
-> service matches
-> email drafts
-> human reviews
-> send logs
-> final package
```

This stage does not add a new data source and does not create unattended Agent
email sending.

## Output Directory

```text
data/processed/result_packages/TASK_<task_id>/
```

Files:

```text
scholarlead_results.xlsx
customers.csv
papers.csv
funding.csv
evidence.csv
service_matches.csv
email_drafts.csv
email_reviews.csv
email_send_logs.csv
task_summary.json
README.txt
```

## Main Code

```text
src/scholarlead_agent/result_package.py
```

Key functions:

```python
build_result_package_from_pubmed_result(...)
build_result_package_from_database_task(...)
```

`build_result_package_from_pubmed_result` remains available for in-memory
PubMed service results.

`build_result_package_from_database_task` is the Stage 37 addition for the
FastAPI boundary. It exports persisted task data by `task_id`.

## API

```text
POST /api/result-packages
GET  /api/result-packages/{package_id}
GET  /api/result-packages/{package_id}/download
```

Request:

```json
{
  "task_id": "task-1",
  "output_dir": "data/processed/result_packages"
}
```

## Workbook Sheets

```text
Customers
Papers
Funding
Evidence
Service_Matches
Email_Drafts
Email_Reviews
Email_Send_Logs
Task_Summary
```

## Notes

- Email drafts are exported as human-review artifacts.
- Email reviews are exported as audit records.
- Send logs include `sent`, `failed`, and `blocked` attempts.
- Permission blockers are preserved.
- Current lead score remains provisional unless a later production scoring
  version is recorded.
- The package builder formats existing data only; it does not rerun PubMed,
  ServiceMatcher, model calls, or email sending.

## Acceptance

- Result Package version is `result-package-v2`.
- `email_reviews.csv` is exported.
- `email_send_logs.csv` is exported.
- `README.txt` is exported.
- Excel workbook includes review and send log sheets.
- `POST /api/result-packages` can build a package from database `task_id`.
- Tests do not access real network or send real email.
