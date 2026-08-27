# ScholarLead Agent

ScholarLead Agent is a Python prototype for overseas scientific customer discovery. The current focus is a PubMed-first workflow with an Agent-ready architecture: collect public literature records, preserve raw evidence, extract candidate research leads, create temporary PubMed-only scores, supplement DOI/publication metadata with Crossref/OpenAlex/NIH RePORTER, build conservative researcher and organization entity drafts, create a minimal evidence-backed official scoring draft, generate human-review email drafts, and export auditable files.

This is still not a complete production delivery. It has a minimal Agent Loop, upgraded Streamlit UI, email draft generation, AI usage logging, Crossref/OpenAlex/NIH RePORTER lookup, conservative entity resolution, a minimal official scoring module, a SQLite foundation, a controlled email-send boundary, and a Stage 28 SMTP test-send entry, but it does not have a production backend, complete production scoring, full approval workflow, production email provider operations, or batch email sending.

## Current Position

The PubMed first-round workflow is implemented as a single-source internal validation chain:

```text
keyword/date/max_results
-> PubMed ESearch / EFetch
-> raw response storage
-> paper parsing and deduplication
-> email evidence from affiliation text
-> lead generation and deduplication
-> basic institution/country identification
-> keyword and service type matching
-> PubMed-only temporary scoring
-> papers/leads JSON and CSV export
-> run report
```

The workflow is deterministic Python logic and is covered by pytest tests. Tests mock HTTP and must not access the real network.

The current Agent layer can call:

```text
search_pubmed
search_crossref
search_openalex
search_funding
generate_email_draft
```

`search_crossref` supplements DOI and publication metadata only. It does not generate leads, score leads, infer active funding, or send email.
`search_openalex` supplements OpenAlex Works metadata and unified paper evidence. It does not generate leads, score leads, infer funding, or send email.
`search_funding` searches NIH RePORTER project records as explicit NIH funding evidence only. NIH RePORTER does not cover all funding sources and is not official scoring.

## Implemented

- Standard `src` Python project structure.
- Python package: `scholarlead_agent`.
- OpenAlex Works collection and regression tests.
- Crossref Works metadata collection and regression tests.
- OpenAlex Service / `search_openalex` Agent Tool.
- NIH RePORTER funding collection and `search_funding` Agent Tool.
- Conservative Researcher / Organization / Contact / Evidence resolution from PubMed Leads.
- Minimal evidence-backed official four-dimension scoring module.
- Multi-source Agent scheduling prompt and fake-model regression tests.
- PubMed ESearch / EFetch client with timeout, User-Agent, and retry behavior.
- PubMed raw ESearch JSON, EFetch XML, and request metadata saving.
- PubMed XML parsing into structured paper records.
- PubMed paper deduplication by DOI first, then PMID.
- Email extraction only from PubMed affiliation text.
- Lead generation, lead deduplication, and manual review marking.
- Basic institution and country identification from affiliation.
- Keyword matching and service type tagging.
- PubMed-only temporary scoring and priority assignment.
- Processed papers/leads JSON and CSV export.
- Run Report generation.
- CLI end-to-end orchestration.
- Reusable PubMed Service.
- Agent ToolRegistry and bounded Agent Loop.
- OpenAI-compatible model adapter.
- `search_pubmed`, `search_crossref`, `search_openalex`, `search_funding`, and `generate_email_draft` tools.
- Streamlit lightweight UI.
- Streamlit Stage 22 view for sources, steps, papers, leads, researchers, funding, scoring evidence, drafts, reports, downloads, and AI usage.
- English email draft generation for human review only.
- Email draft review status, send permission policy, and audit record design.
- SQLite database foundation with schema initialization and core insert helpers.
- Controlled email-send boundary with explicit provider injection and send logs.
- SMTP test-send provider and Streamlit manual test-send entry for whitelisted test recipients.
- AI usage / token logging to JSONL.

## Not Implemented In This Round

- Other funding sources such as NSF.
- ORCID or other researcher identity enrichment.
- Formal multi-source lead merging.
- Complete production scoring with all evidence sources.
- Production email provider operations for real customer outreach.
- Batch email sending or unattended sending.
- Agent-accessible `send_email` tool.
- Database-backed email review workspace.
- Production database-backed workspace.
- Production customer management platform.

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

## NCBI Configuration

Copy `.env.example` to `.env` for local use if needed:

```powershell
copy .env.example .env
```

Placeholders:

```text
NCBI_TOOL=ScholarLeadAgent
NCBI_EMAIL=your.email@example.com
NCBI_API_KEY=
```

Do not commit real credentials. `NCBI_API_KEY` is optional for the first round.

Optional Crossref configuration:

```text
CROSSREF_BASE_URL=https://api.crossref.org
CROSSREF_USER_AGENT=ScholarLeadAgent/0.1 (set CROSSREF_MAILTO for contact)
CROSSREF_MAILTO=
```

Optional NIH RePORTER configuration:

```text
NIH_REPORTER_BASE_URL=https://api.reporter.nih.gov
NIH_REPORTER_PROJECTS_SEARCH_URL=https://api.reporter.nih.gov/v2/projects/search
NIH_REPORTER_USER_AGENT=ScholarLeadAgent/0.1 (set NCBI_EMAIL for contact)
```

## Run PubMed First-Round Workflow

Run from the project root:

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.pubmed_main `
  --query "single-cell RNA sequencing cancer" `
  --from-date 2024-01-01 `
  --to-date 2024-12-31 `
  --max-results 10 `
  --country us `
  --service-type scRNA-seq
```

This command makes real PubMed requests. Use a small `--max-results` value for first checks.

Inputs:

- `--query`: PubMed search keywords.
- `--from-date`: publication start date, `YYYY-MM-DD`.
- `--to-date`: publication end date, `YYYY-MM-DD`.
- `--max-results`: maximum PubMed results.
- `--country`: optional target country label for run context.
- `--service-type`: optional service type label for lead tagging.
- `--raw-dir`: optional raw output directory, default `data/raw/pubmed`.
- `--processed-dir`: optional processed output directory, default `data/processed/pubmed`.

## Outputs

Raw files:

```text
data/raw/pubmed/*_esearch.json
data/raw/pubmed/*_efetch.xml
data/raw/pubmed/*_request_meta.json
```

Processed files:

```text
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.json
data/processed/pubmed/pubmed_papers_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.json
data/processed/pubmed/pubmed_leads_{query}_{timestamp}.csv
data/processed/pubmed/pubmed_run_report_{query}_{timestamp}.json
```

`pubmed_papers_*.csv` contains paper-level records. `pubmed_leads_*.csv` contains candidate researcher/customer leads. `pubmed_run_report_*.json` records inputs, counts, file paths, status, and errors.

NIH RePORTER funding outputs are stored separately:

```text
data/raw/nih_reporter/nih_reporter_{query}_{timestamp}_projects.json
data/raw/nih_reporter/nih_reporter_{query}_{timestamp}_request_meta.json
data/processed/nih_reporter/nih_reporter_funding_{query}_{timestamp}.json
data/processed/nih_reporter/nih_reporter_funding_{query}_{timestamp}.csv
data/processed/nih_reporter/nih_reporter_run_report_{query}_{timestamp}.json
```

## Run Streamlit UI

After installing dependencies, run from the project root:

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

The UI reuses the same PubMed service as the CLI. Clicking the PubMed run button makes real PubMed requests, so start with a small `max_results` value such as `3` or `5`.

The page supports Chinese / English switching from the sidebar language selector.

The UI includes:

- data source visibility;
- Agent tool-call summary;
- PubMed papers and leads;
- researcher / organization draft entities;
- NIH RePORTER funding rows when returned by Agent `search_funding`;
- official scoring draft rows with missing evidence clearly marked;
- human-review email draft generation and download;
- email draft review decision saving and permission blocker display;
- run report and file downloads;
- AI usage view.

Model-backed features require local `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` configuration. Stage 28 can send a single manual SMTP test email only when `.env` explicitly enables it and the recipient is the configured test/allowed address.

## Run FastAPI Backend

Stage 34B adds a thin FastAPI boundary over the existing Python modules. It is
for the future Vue frontend and does not replace the CLI or Streamlit yet.

Run from the project root:

```powershell
$env:PYTHONPATH="src"
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

OpenAPI docs:

```text
http://127.0.0.1:8000/docs
```

## Run Vue Frontend Skeleton

Stage 34C adds the first Vue skeleton in `frontend/`. It calls FastAPI only and
does not contain API keys, SMTP credentials, or direct external-data-source
calls.

In a second PowerShell window:

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

Default API base URL:

```text
http://127.0.0.1:8000
```

Optional override:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Email Review And Permission Design

Stage 23 defines review states and send permission checks for email drafts. By
default, sending is blocked because real email sending is disabled, no sender
account is configured, and no quota is configured. The current system can
record review decisions and audit records, but it still does not send email.

Optional audit directory:

```text
EMAIL_AUDIT_DIR=data/processed/email_audit
```

## SQLite Database Foundation

Stage 24 adds a minimal SQLite schema for later product workflows. It does not
replace raw files or JSON / CSV exports.

Initialize the database:

```powershell
.\literature_env\Scripts\python.exe -m scholarlead_agent.database_main --show-tables
```

Default database path:

```text
data/processed/scholarlead_agent.sqlite
```

Optional environment variable:

```text
DATABASE_PATH=data/processed/scholarlead_agent.sqlite
```

## Controlled Email Send Boundary

Stage 25 adds a code-level send loop around approved email drafts. It checks
`PermissionPolicy`, requires a verified email, writes audit/send status records,
and only calls a provider when trusted application code explicitly injects one.

Stage 28 adds an SMTP test-send provider and Streamlit manual test-send panel.
It is limited to approved drafts and configured test/allowed recipients. The
project still does not register a `send_email` Agent Tool and does not support
unattended or batch outreach.

Stage 35 adds batch email draft generation for persisted leads. Stage 36 adds
batch review and controlled batch send boundaries. The safest send mode is
`permission_check`, which records blockers and does not call an email provider.
`test_recipient` and `real_recipient` modes require backend configuration and
permission checks.

Stage 37 upgrades Result Package export to v2. The package now includes
`email_reviews.csv`, `email_send_logs.csv`, and `README.txt`, and
`POST /api/result-packages` can build an export package from a persisted
database `task_id`.

Stage 38 defines the adapter specification for future data sources. New sources
must provide client, parser, service, tool adapter, unified converter, raw
storage, processed export, mocked tests, run report, and source metadata before
being exposed through Agent tools or frontend workflows.

## Temporary Scoring Notice

The current score is a PubMed-only temporary score:

```text
topic_match_score: 50%
publication_recency_score: 30%
email_contactability_score: 20%
```

It is not the official four-dimension scoring required by the full project. Funding and outsourcing dimensions intentionally remain unscored:

```text
funding_activity_score = null
funding_activity_reason = Funding source not connected in PubMed-only first round
outsourcing_tendency_score = null
official_scoring_status = pending_multi_source_data
```

## Official Scoring Draft Notice

The Stage 21F official scoring module exists as a minimal evidence-backed draft.
It uses fixed weights:

```text
funding_activity: 40%
research_direction_match: 30%
publication_recency: 20%
outsourcing_tendency: 10%
```

If a dimension lacks explicit evidence, the official total score remains empty
and the missing dimension is recorded. The module does not let the LLM invent
scores or infer funding from PubMed papers.

## Run Tests

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

Tests must not access the real network. PubMed, Crossref, OpenAlex, and NIH RePORTER HTTP behavior is mocked in tests.

## Safety Rules

- Preserve raw source data before processing.
- Do not guess missing emails.
- Do not treat a candidate PI as a confirmed corresponding author.
- Do not hard-code API keys, passwords, SMTP credentials, or tokens.
- Do not commit `.env`.
- Do not claim PubMed temporary scoring is official four-dimension scoring.
- Do not claim the first round is a complete Agent, T+45, or final delivery.
- Do not claim Crossref funder metadata proves active funding.
- Do not send real email from the current system.
- Do not expose a `send_email` Agent Tool before review, permission, quota, and provider integration are complete.

## Documentation

Detailed planning and stage documents are in `docs/`, including:

- `pubmed_first_round_implementation_plan_v2.md`
- `pubmed_first_round_implementation_plan_v2.5.md`
- `pubmed_stage10_lead_dedup.md`
- `pubmed_stage11_keyword_matching.md`
- `pubmed_stage12_temporary_scoring.md`
- `pubmed_stage13_processed_export.md`
- `pubmed_stage14_run_report.md`
- `pubmed_stage15_end_to_end_cli.md`
- `pubmed_stage18_streamlit_ui.md`
- `pubmed_stage21a_crossref.md`
- `pubmed_stage21b_unified_models.md`
- `pubmed_stage21c_openalex_agent.md`
- `pubmed_stage23_email_review_permission.md`
- `pubmed_stage24_database_foundation.md`
- `pubmed_stage25_email_send_loop.md`
- `pubmed_stage26_demo_validation.md`
- `pubmed_stage27_email_provider_decision.md`
- `pubmed_stage28_smtp_test_send.md`
- `pubmed_stage29_lead_detail_evidence.md`
- `pubmed_stage30_conversation_task_context.md`
- `pubmed_stage31_service_catalog_matcher.md`
- `pubmed_stage32_auto_email_draft_sender_profile.md`
- `pubmed_stage33_result_package_v1.md`
- `pubmed_stage34_background_job_foundation.md`
- `pubmed_stage34a_api_boundary_design.md`
- `pubmed_stage34c_vue_frontend_skeleton.md`
- `pubmed_stage35_batch_email_drafts.md`
- `pubmed_stage36_batch_review_send.md`
- `pubmed_stage37_result_package_v2.md`
- `pubmed_stage38_data_source_adapter_spec.md`




