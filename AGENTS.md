# AGENTS.md

This file defines development rules for Codex and other AI coding assistants working on ScholarLead Agent.

## Project Mission

ScholarLead Agent, also referred to as BioLead in planning documents, is an evidence-first scientific lead discovery and outreach workflow prototype. It helps users move from research keywords or natural-language intent to public scientific evidence, structured lead records, scoring signals, service matching, reviewed email drafts, controlled sending, and auditable exports.

The long-term workflow is:

```text
user query
-> Agent / task
-> public scientific data collection
-> raw data preservation
-> cleaning and normalization
-> unified models and evidence records
-> researcher / organization / lead identification
-> scoring
-> company service matching
-> personalized email draft
-> human review
-> controlled send boundary
-> result package / report / export
```

Do not optimize one isolated module in a way that damages this full workflow.

## Current Project Baseline

Current implementation baseline: Stage 38.

Existing architecture includes:

- PubMed / Crossref / OpenAlex / NIH RePORTER integrations.
- Unified models and evidence records.
- Researcher, organization, contact, paper, funding, and lead structures.
- ToolRegistry and bounded Agent Loop.
- OpenAI-compatible model adapter.
- Conversation / task context.
- SQLite persistence foundation.
- Company Service Catalog and ServiceMatcher.
- SenderProfile.
- Personalized email draft generation.
- Human review and controlled send boundaries.
- SMTP test-send provider.
- Batch email draft, review, and controlled batch send workflow.
- Background job foundation.
- FastAPI backend.
- Vue frontend.
- Streamlit prototype UI.
- Result Package v2.
- Data Source Adapter specification.

PubMed remains the current primary lead-discovery path. Other sources are present as first-version integrations or supporting evidence sources, not complete production-grade data products.

## Source of Truth Priority

When project documents disagree, use this order:

1. Explicit current user instruction.
2. `AGENTS.md` / `AGENT_cn.md`.
3. `docs/current_project_status.md`.
4. `docs/feature_acceptance_matrix.md`.
5. `README.md` / `README_cn.md`.
6. Current next-plan document.
7. Stage implementation documents.
8. Superseded historical planning documents.

Stage documents describe historical implementation decisions and must not be used alone to infer the current project state. Historical or superseded planning documents must not be used as the current development entry point.

## No Duplicate Subsystems

Do not create a second implementation of an existing subsystem.

Before adding a new module, verify whether an equivalent implementation already exists under:

```text
src/scholarlead_agent/
frontend/
docs/
tests/
```

Extend the current architecture unless the user explicitly approves replacement.

Avoid duplicate versions of:

- Agent Loop.
- ToolRegistry.
- SQLite/database layer.
- Email review and sending workflow.
- FastAPI app.
- Vue frontend shell.
- ServiceMatcher.
- Result package generation.
- Data source adapter pattern.

## Python Rules

- Support Python 3.11 and newer.
- Current local virtual environment name: `literature_env`.
- Use the existing `src` layout.
- Main package name: `scholarlead_agent`.
- Keep code beginner-friendly and testable.
- Add type hints to public functions.
- Keep functions small.
- Add comments only when the logic is not obvious.
- Avoid unrelated refactoring.

## Security Rules

- Never write passwords, API keys, SMTP credentials, OAuth tokens, or database passwords directly in code.
- Read secrets from environment variables or local `.env` files.
- Never commit `.env`.
- Keep only placeholder values in `.env.example`.
- Do not log secrets.
- Do not expose real recipient lists, customer emails, or model keys in documentation examples.

## Data Rules

- Prefer official APIs over scraping.
- Preserve raw API responses before cleaning.
- Preserve source provenance whenever possible.
- Record the source of extracted information.
- Do not guess missing author emails.
- Do not invent ORCID, institution, funding, grant amount, author role, or research direction.
- Do not treat inferred information as confirmed fact.
- Mark uncertain records for manual review.

Recommended provenance fields:

```text
source_name
source_type
source_id
source_url
retrieved_at
```

## Data Source Architecture

External scientific data sources should follow the Stage 38 adapter direction:

```text
Client
Parser
Service
Tool Adapter
Unified Converter
Raw Storage
Processed Export
Mocked Tests
Run Report
Source Metadata
EvidenceRecord
```

Business logic must not depend directly on one third-party API JSON shape.

Do not:

- Call external scientific APIs directly from Vue.
- Call external scientific APIs directly from a FastAPI route without a service layer.
- Skip raw storage.
- Skip `EvidenceRecord` when evidence is used downstream.
- Feed raw external fields directly into email generation without normalization.
- Register a new Agent Tool without mocked tests.
- Use an LLM to guess emails, grants, identities, institutions, or countries.

Every external API integration should handle timeout, retries, rate limits, pagination, empty responses, HTTP errors, malformed responses, and practical schema changes. A later API failure must not delete already saved raw or processed data.

## Email Rules

The system supports controlled email workflows through draft generation, human review, permission checks, and logged sending. It does not support unattended Agent-driven outreach.

Important boundaries:

- No Agent-accessible `send_email` tool is registered.
- Agents may generate or prepare drafts, but must not send emails autonomously.
- Real sending must pass explicit user/human action and permission policy checks.
- Batch sending must keep limits, idempotency, status logs, and failure records.
- Missing emails must remain missing. Do not infer or fabricate contact addresses.

## Testing Rules

- Add or update tests for every behavioral change.
- Tests for external APIs must mock HTTP and must not access the real network.
- Keep regression tests for existing PubMed, Crossref, OpenAlex, NIH RePORTER, Agent, database, email, API, and frontend behavior.
- Run the relevant focused tests first, then full regression when a change can affect shared behavior.

Current full regression command:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

## Documentation Rules

After each completed stage, update:

- `docs/current_project_status.md`
- `docs/feature_acceptance_matrix.md`

Update `README.md` / `README_cn.md` when user-visible behavior changes.

Do not rewrite Stage 1-38 implementation documents unless there is a factual error, file corruption, or obvious encoding issue. They are historical implementation records.

The current development entry point after Stage 38 is `docs/ScholarLead_Agent_next_plan_v2.8.md`.
