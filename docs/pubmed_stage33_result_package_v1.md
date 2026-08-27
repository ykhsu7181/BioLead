# PubMed Stage 33: Result Package v1

## Scope

Stage 33 adds a first Result Package exporter for one completed PubMed task.

It only exports already available artifacts. It does not rerun:

- PubMed collection
- Lead generation
- researcher merging
- ServiceMatcher
- scoring
- email draft generation
- email sending

## Output Directory

Default output:

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
task_summary.json
```

## Service

Implemented in:

```text
src/scholarlead_agent/result_package.py
```

Main entry:

```python
build_result_package_from_pubmed_result(result)
```

The function accepts optional already-created:

- `funding_rows`
- `service_match_rows`
- `email_drafts`

When email drafts contain `matched_service` evidence, `service_matches.csv` can be derived from that existing evidence. If no such evidence is present, service match rows stay empty. This avoids silently rerunning ServiceMatcher.

## Core Fields

`customers.csv` includes:

- `Task_ID`
- `Researcher_ID`
- `Lead_ID`
- `PI_Name`
- `Verified_Email`
- `Email_Status`
- `Institution`
- `Country`
- `Recent_Publication_Title`
- `PMID`
- `DOI`
- `Lead_Score`
- `Priority`
- `Scoring_Version`
- `Scoring_Status`
- `Matched_Service_ID`
- `Matched_Service_Name`
- `Service_Match_Score`
- `Manual_Review_Required`
- `Source_Links`

Current scoring metadata is explicit:

```text
Scoring_Version = draft-v1
Scoring_Status = provisional
```

## Excel Workbook

The workbook contains:

- `Customers`
- `Papers`
- `Funding`
- `Evidence`
- `Service_Matches`
- `Email_Drafts`
- `Task_Summary`

The workbook is generated with the Python standard library, so no new Excel dependency is required.

## Streamlit Entry

The Downloads tab now has:

```text
Generate Result Package v1 / 生成结果包 v1
```

This creates the package from the current run result and displays the generated file paths.

## Validation

Related tests:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_result_package.py tests\test_pubmed_ui.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
