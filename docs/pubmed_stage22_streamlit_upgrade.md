# Stage 22: Streamlit Frontend Upgrade

## Goal

Stage 22 upgrades the existing Streamlit page so a user can inspect a small
end-to-end run from one place.

This is still a lightweight demo UI. It is not a production front end, does not
use a database, and does not send real email.

## Main Views

The page now includes a sidebar language selector for Chinese / English display.

- Current scope
- Agent / natural language task
- PubMed search task
- Data sources
- Workflow steps
- Papers
- Leads
- Researchers and organizations
- Funding evidence
- Official scoring draft
- Human-review email draft
- Run report
- Downloads
- AI usage

## Data Source Display

The UI shows whether each source is used or available:

- PubMed
- Crossref
- OpenAlex
- NIH RePORTER

PubMed is the main lead-discovery path. Crossref and OpenAlex are enrichment
sources. NIH RePORTER is explicit NIH funding evidence only.

## Researcher / Organization Display

The UI uses the Stage 21E conservative entity-resolution helpers:

- same verified email can merge researchers;
- same name alone does not auto-merge;
- conflicting identity signals are marked for manual review;
- organization rows keep source lead IDs.

## Funding Display

Funding rows are shown when the Agent has called `search_funding` and returned
NIH RePORTER records.

If no funding evidence is attached, the page says so directly. It does not infer
funding from PubMed papers.

## Scoring Display

The UI shows Stage 21F official scoring draft rows.

If funding or outsourcing evidence is missing, the official total score remains
empty and the missing dimensions are shown.

## Email Draft Display

The UI can generate and edit a human-review English email draft when model
configuration exists.

There is no real send button.

## Run Command

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

## Tests

Frontend helper coverage is in:

```text
tests/test_pubmed_ui.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
