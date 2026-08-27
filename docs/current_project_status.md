# ScholarLead Agent Current Project Status

Version: v1.0  
Date: 2026-08-27  
Branch: main  
Current Stage: Stage 38  
Next Entry Point: Stage 39

## 1. Current Baseline

ScholarLead Agent, also referred to as BioLead in planning documents, is currently an evidence-first scientific lead discovery and outreach workflow prototype.

The project has moved beyond the early PubMed-only prototype. It now has a Python service layer, Agent orchestration, SQLite persistence, controlled email workflow boundaries, a FastAPI backend, a Vue frontend, a Streamlit prototype UI, and auditable result package export.

PubMed remains the primary lead-discovery path. Crossref, OpenAlex, and NIH RePORTER are available as first-version or supporting data-source integrations.

## 2. Current Architecture

```text
Vue frontend / Streamlit prototype
-> FastAPI / CLI
-> Service layer
-> Agent tools / deterministic business logic
-> Unified models and EvidenceRecord
-> PubMed / Crossref / OpenAlex / NIH RePORTER
-> SQLite / raw files / processed exports / result packages
```

## 3. Implemented

- Standard Python `src` project structure and `scholarlead_agent` package.
- PubMed ESearch / EFetch collection, parsing, raw storage, processed export, run report, and tests.
- PubMed paper and lead deduplication.
- PubMed affiliation email extraction with evidence source tracking.
- Basic institution and country identification from affiliations.
- Keyword matching, service type tagging, temporary PubMed scoring, and priority labels.
- Crossref Works metadata lookup.
- OpenAlex Works metadata lookup.
- NIH RePORTER funding lookup.
- Unified paper, researcher, organization, contact, funding, lead, and evidence models.
- Minimal evidence-backed official scoring draft.
- ToolRegistry and bounded Agent Loop.
- OpenAI-compatible model adapter.
- Conversation and task context.
- Company Service Catalog.
- ServiceMatcher.
- SenderProfile.
- AI email draft generation for human review.
- Human review status and permission policy.
- SMTP test-send provider and controlled send logs.
- Batch email draft generation.
- Batch review and controlled batch send.
- SQLite schema initialization and insert/query helpers.
- AI usage logging.
- Background job foundation.
- FastAPI API boundary.
- Vue frontend skeleton with PubMed search and result package download.
- Streamlit prototype UI.
- Result Package v2.
- Data Source Adapter specification.

## 4. Partially Implemented

- Vue frontend: basic shell and selected workflows are present; not all Streamlit workflows are fully migrated.
- Multi-source entity resolution: conservative first version exists; production-grade merging still needs stronger matching and review.
- Official scoring: minimal evidence-backed draft exists; production scoring still needs confirmed business rules and richer evidence.
- Email operations: test/controlled sending exists; production provider operations, deliverability, unsubscribe handling, suppression management, and campaign governance are not complete.
- Agent conversation: task context exists; robust long-context multi-turn business memory is still limited.
- Data source adapter: specification exists; not every source has been migrated to the full adapter standard.

## 5. Not Implemented

- ORCID integration.
- NSF / CORDIS and additional funding sources.
- Production-grade multi-source identity merging.
- Complete production scoring.
- Production deployment.
- Production-grade email provider operations.
- Unattended Agent-driven sending.
- Agent-accessible `send_email` tool.
- Full CRM / sales follow-up workflow.
- Production-scale distributed job queue.
- Complete Vue migration of every historical Streamlit feature.

## 6. Safety / Product Boundaries

- Do not guess missing emails, ORCID, grants, institution identity, country, or author role.
- Do not treat inferred values as confirmed facts.
- Preserve raw API responses before cleaning when collecting external data.
- Keep source evidence and provenance for downstream decisions.
- Tests for external APIs must mock HTTP and must not access the real network.
- Agents may prepare drafts and analysis, but must not send emails autonomously.
- Real email sending must pass human review, permission policy, allowlist/limits where configured, and logging.

## 7. Current Source of Truth

When documents conflict, use this order:

1. Explicit current user instruction.
2. `AGENTS.md` / `AGENT_cn.md`.
3. `docs/current_project_status.md`.
4. `docs/feature_acceptance_matrix.md`.
5. `README.md` / `README_cn.md`.
6. Current next-plan document.
7. Stage implementation documents.
8. Superseded historical planning documents.

Stage implementation documents record what was true at that stage. They are not the current project baseline by themselves.

## 8. Next Development Entry Point

Current Stage: Stage 38  
Next Stage: Stage 39  
Current next-plan document: `docs/ScholarLead_Agent_next_plan_v2.8.md`

Stage 39 should extend the existing architecture. It should not reimplement PubMed, Agent Loop, ToolRegistry, SQLite, FastAPI, Vue skeleton, ServiceMatcher, email review, batch draft, result package, or data source adapter logic from scratch.
