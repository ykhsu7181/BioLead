# ScholarLead Agent

ScholarLead Agent is a Python prototype for overseas scientific customer discovery. The current focus is a deterministic PubMed first-round workflow: collect public literature records, preserve raw evidence, extract candidate research leads, create temporary PubMed-only scores, and export auditable files for human review.

This first round is not a complete AI Agent delivery. It does not use an LLM, Agent Loop, database, web UI, or real email sending.

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

## Implemented

- Standard `src` Python project structure.
- Python package: `scholarlead_agent`.
- OpenAlex Works collection and regression tests.
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

## Not Implemented In This Round

- Crossref.
- Funding sources such as NIH RePORTER or NSF.
- ORCID or other researcher identity enrichment.
- Multi-source lead merging.
- Official four-dimension scoring.
- LLM calls.
- Agent Loop or ToolRegistry.
- Personalized email draft generation.
- Real email sending.
- Streamlit or other web UI.
- Database storage.
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

## Run Lightweight Streamlit UI

After installing dependencies, run from the project root:

```powershell
.\literature_env\Scripts\python.exe -m streamlit run src\scholarlead_agent\ui\streamlit_app.py
```

The UI reuses the same PubMed service as the CLI. Clicking the run button makes real PubMed requests, so start with a small `max_results` value such as `3` or `5`.

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

## Run Tests

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

Tests must not access the real network. PubMed and OpenAlex HTTP behavior is mocked in tests.

## Safety Rules

- Preserve raw source data before processing.
- Do not guess missing emails.
- Do not treat a candidate PI as a confirmed corresponding author.
- Do not hard-code API keys, passwords, SMTP credentials, or tokens.
- Do not commit `.env`.
- Do not claim PubMed temporary scoring is official four-dimension scoring.
- Do not claim the first round is a complete Agent, T+45, or final delivery.

## Documentation

Detailed planning and stage documents are in `docs/`, including:

- `pubmed_first_round_implementation_plan_v2.md`
- `pubmed_stage10_lead_dedup.md`
- `pubmed_stage11_keyword_matching.md`
- `pubmed_stage12_temporary_scoring.md`
- `pubmed_stage13_processed_export.md`
- `pubmed_stage14_run_report.md`
- `pubmed_stage15_end_to_end_cli.md`
- `pubmed_stage18_streamlit_ui.md`
