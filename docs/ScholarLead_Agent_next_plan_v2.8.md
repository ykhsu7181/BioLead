# ScholarLead Agent Next Development Plan v2.8

Version: v2.8  
Date: 2026-08-27  
Current baseline: Stage 38  
Next stage: Stage 39  
Project name: ScholarLead Agent / BioLead planning direction

## 1. Document Purpose

This document is the current next-plan entry after Stage 38.

It replaces `docs/ScholarLead_Agent_next_plan_v2.7.md` as the future development entry point. The v2.7 plan is kept as a completed historical plan for Stage 30 through Stage 38.

Stage 39 and later work must extend the current implementation instead of rebuilding existing subsystems.

## 2. Current Baseline

Already implemented by Stage 38:

- PubMed primary workflow.
- Crossref, OpenAlex, and NIH RePORTER first-version integrations.
- Unified models and evidence records.
- Researcher, organization, contact, funding, paper, and lead structures.
- Conservative entity resolution drafts.
- Temporary PubMed scoring and minimal evidence-backed official scoring draft.
- Agent Loop and ToolRegistry.
- OpenAI-compatible model adapter.
- Conversation / Task Context.
- Company Service Catalog and ServiceMatcher.
- SenderProfile.
- AI email draft generation for human review.
- Human review and permission policy.
- SMTP test-send and send logs.
- Batch email draft, review, and controlled send.
- SQLite foundation.
- Background job foundation.
- FastAPI API boundary.
- Vue frontend skeleton with selected migrated workflows.
- Streamlit prototype UI.
- Result Package v2.
- Data Source Adapter specification.

## 3. Non-Reimplementation Rule

Stage 39 must not reimplement:

- PubMed collection and parsing.
- Agent Loop.
- ToolRegistry.
- SQLite foundation.
- FastAPI app.
- Vue shell.
- ServiceMatcher.
- Email review workflow.
- Batch draft workflow.
- Result Package.
- Data Source Adapter pattern.

New work should be implemented as extensions, adapters, services, API routes, UI panels, tests, or documentation updates inside the existing architecture.

## 4. Recommended Stage 39 Direction

Stage 39 should focus on making the current demo workflow easier to use and harder to misuse.

Recommended scope:

1. Stabilize Vue as the primary demo UI.
2. Continue migrating key Streamlit-only workflows to Vue.
3. Improve end-to-end result visibility:
   - search inputs
   - data-source summary
   - leads
   - paper evidence
   - service match
   - email draft status
   - result package download
4. Improve batch email safety display:
   - draft counts
   - reviewed counts
   - blocked counts
   - sent / failed counts
   - allowlist / daily limit warnings
5. Keep Streamlit as a prototype/reference UI until Vue covers the needed demo path.

Expected result:

```text
User can run a small PubMed-based workflow from Vue,
inspect leads and evidence,
generate or view related output,
and download a result package.
```

## 5. Recommended Stage 40 Direction

Stage 40 should improve business workflow completeness around leads and email drafts.

Recommended scope:

- Lead detail page improvements.
- Evidence timeline / source display.
- Service match explanation.
- Draft generation and draft refresh entry.
- SenderProfile display.
- Manual review actions.
- Clear blocked-send reasons.

Expected result:

```text
User can inspect a lead, understand why it was selected,
see what company service matched it,
review the generated email draft,
and decide whether it is eligible for sending.
```

## 6. Recommended Stage 41 Direction

Stage 41 should improve production-readiness boundaries without turning the prototype into a full production system too early.

Recommended scope:

- Stronger email suppression and allowlist handling.
- Safer batch-send limits.
- Better job status persistence.
- More explicit failure reports.
- Configuration validation.
- Documentation for test email providers.

Expected result:

```text
The controlled email workflow remains safe during demos
and small internal tests.
```

## 7. Later Data Source Expansion

Additional data sources should follow the Stage 38 data source adapter standard:

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

Potential later sources:

- ORCID.
- NSF.
- CORDIS.
- Europe PMC.
- bioRxiv / medRxiv, if compliant access is confirmed.
- Other lawful and stable public scientific data sources.

Do not connect a new source directly from Vue or directly inside a FastAPI route.

## 8. Current Open Questions

- Whether BioLead should become the formal product name while keeping `scholarlead_agent` as the code package.
- Which Vue workflows must be complete before Streamlit can be deprecated.
- Which company service catalog fields are required for real internal use.
- Which email provider and compliance requirements are needed before any production outreach.
- Whether CRM/follow-up should be built locally or integrated with an external tool.

## 9. Documentation Maintenance

When a new stage is completed, update:

- `docs/current_project_status.md`
- `docs/feature_acceptance_matrix.md`

Update `README.md` and `README_cn.md` if user-visible behavior changes.

Keep Stage 1-38 documents as historical implementation records.
