# ScholarLead Agent

ScholarLead Agent is an evidence-first scientific lead discovery and outreach workflow prototype. It combines a Python/FastAPI backend, Vue frontend, Streamlit prototype UI, Agent orchestration, multi-source scientific data integration, controlled email workflows, and auditable result export.

Planning documents may also refer to the product direction as BioLead. The Python package remains `scholarlead_agent`.

This is not a production system yet.

## Current Position

Current baseline: Stage 38.

```text
User Query
-> Agent / Task
-> PubMed / Crossref / OpenAlex / NIH RePORTER
-> Unified Models + Evidence
-> Researcher / Organization / Lead
-> Scoring
-> Company Service Matching
-> Personalized Email Draft
-> Human Review
-> Controlled Send Boundary
-> Result Package
```

PubMed remains the current primary lead-discovery path. Crossref, OpenAlex, and NIH RePORTER are available as first-version or supporting evidence sources.

## Implemented

- Standard `src` Python project structure and `scholarlead_agent` package.
- PubMed ESearch / EFetch collection, parsing, raw storage, processed export, run report, and tests.
- PubMed email extraction from affiliation text only.
- Paper and lead deduplication.
- Basic institution and country identification.
- Keyword matching, service type tagging, temporary PubMed scoring, and priority labels.
- Crossref Works lookup.
- OpenAlex Works lookup.
- NIH RePORTER funding lookup.
- Unified models and evidence records.
- Conservative researcher / organization / contact / lead structures.
- Minimal evidence-backed official scoring draft.
- ToolRegistry and bounded Agent Loop.
- OpenAI-compatible model adapter.
- Conversation / task context.
- Company Service Catalog and ServiceMatcher.
- SenderProfile.
- AI email draft generation for human review.
- Human review and permission policy.
- SQLite persistence foundation.
- SMTP test-send provider and send logs.
- Batch email draft generation.
- Batch review and controlled batch send.
- Background job foundation.
- FastAPI API boundary.
- Vue frontend skeleton with PubMed search, result display, and result package download.
- Streamlit prototype UI.
- Result Package v2.
- Data Source Adapter specification.
- AI usage logging.

## Not Implemented

- ORCID integration.
- NSF / CORDIS and additional funding sources.
- Production-grade multi-source entity merging.
- Complete production scoring.
- Production deployment.
- Production-grade email provider operations.
- Unattended Agent-driven outreach.
- Agent-accessible `send_email` tool.
- Full CRM / sales follow-up workflow.
- Production-scale distributed job queue.
- Complete Vue migration of every historical Streamlit feature.

## Email Boundary

The system supports controlled batch email workflows through human review, permission checks, and send logs.

It does not support unattended Agent-driven outreach.

No Agent Tool named `send_email` is registered. Agents may generate or prepare drafts, but real sending must be triggered through an explicit reviewed workflow.

## Environment

Python:

```text
Python 3.11+
```

Current local virtual environment:

```text
literature_env
```

Install from the project root:

```powershell
cd "D:\ScholarLead Agent"
.\literature_env\Scripts\python.exe -m pip install -r requirements.txt
.\literature_env\Scripts\python.exe -m pip install -e .
```

## Configuration

Copy `.env.example` to `.env` for local configuration:

```powershell
copy .env.example .env
```

Do not commit real secrets.

Common optional settings include:

```text
NCBI_TOOL=
NCBI_EMAIL=
NCBI_API_KEY=

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=
OPENAI_FALLBACK_MODEL=

EMAIL_PROVIDER=smtp
EMAIL_SEND_ENABLED=false
EMAIL_SENDER=
EMAIL_TEST_RECIPIENT=
EMAIL_ALLOWED_RECIPIENTS=
EMAIL_DAILY_LIMIT=5

SMTP_HOST=
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_USE_SSL=true
SMTP_TIMEOUT_SECONDS=30
```

## Run PubMed CLI

From the project root:

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 5 `
  --country us `
  --service-type scRNA-seq
```

This command may access the real PubMed API. For a first check, keep `--max-results` small, such as `3` or `5`.

## Run Streamlit Prototype

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

Streamlit remains a prototype UI. It includes PubMed search, Agent tasks, lead details, email drafts, send-test entry, and result views.

## Run FastAPI Backend

```powershell
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## Run Vue Frontend

In another PowerShell window:

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

The Vue frontend currently contains the frontend shell plus migrated PubMed search, result display, and result package generation/download.

## Output Files

Raw PubMed files:

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
```

Processed PubMed files:

```text
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_run_report_{query}_{timestamp}.json
```

Result packages are generated under the configured processed/export output area and can also be downloaded from supported UI/API flows.

## Run Tests

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

Tests for external APIs must mock HTTP and must not access the real network.

## Current Documentation

- Current status: `docs/current_project_status.md`
- Feature matrix: `docs/feature_acceptance_matrix.md`
- Current next plan: `docs/ScholarLead_Agent_next_plan_v2.8.md`
- Historical stage records: `docs/pubmed_stage*.md`
