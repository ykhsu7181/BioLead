# AGENTS.md

This file defines development rules for Codex and other AI coding assistants working on ScholarLead Agent.

## Project Mission

ScholarLead Agent is an overseas scientific customer discovery system. It should help users move from research keywords or natural-language intent to structured scientific leads, evidence-backed scoring, customer analysis, exportable reports, and eventually human-reviewed academic outreach.

The long-term business workflow is:

```text
user query
→ search task
→ public scientific data collection
→ raw data preservation
→ cleaning and normalization
→ researcher / PI identification
→ entity deduplication
→ paper / funding / institution / email enrichment
→ lead scoring
→ customer prioritization
→ customer analysis
→ personalized email draft
→ human review
→ confirmed sending
→ follow-up / reporting / export
```

Do not optimize one isolated module in a way that damages this full workflow.

## Current Development Strategy

Build deterministic tools first, then add Agent orchestration.

Preferred sequence:

```text
official data API
→ raw response storage
→ normalized records
→ provenance
→ tests
→ business rules
→ workflow integration
→ optional LLM/Agent layer
```

The first real module already implemented is OpenAlex paper collection. The recommended next main workflow is PubMed.

Do not introduce LLMs, Streamlit, database storage, Crossref, or email sending unless the user explicitly asks for that phase.

## Source of Truth

Project decisions should follow:

- `README.md`
- documents under `docs/`
- the detailed overseas Agent requirements and acceptance criteria
- explicit user instructions in the current conversation

If requirements conflict:

1. Do not silently change the requirement.
2. Record the conflict.
3. Prefer configurable implementation.
4. Ask for confirmation when the business rule is ambiguous.

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

External scientific data sources should be implemented through separate adapters or clearly separated client modules.

Recommended interface concept:

```text
search()
fetch_detail()
normalize()
health_check()
```

Business logic should not depend directly on one third-party API JSON shape.

Every external API integration should handle:

- timeout
- retries
- rate limits
- pagination
- empty responses
- HTTP errors
- malformed responses
- schema changes where practical

Errors must be observable and traceable. A later API failure must not delete already saved raw or processed data.

## Current OpenAlex Rules

OpenAlex collection must:

- use a clear User-Agent
- use a 30-second timeout
- retry 429 and 5xx responses up to 3 times
- limit first-version `max_results` to 20
- restore `abstract_inverted_index`
- normalize DOI by trimming spaces, removing `https://doi.org/`, and lowercasing
- deduplicate by DOI first
- deduplicate by OpenAlex ID when DOI is missing
- save raw responses under `data/raw`
- save processed JSON and CSV under `data/processed`
- avoid real network calls in tests

## Researcher and Customer Rules

Do not merge researchers by name alone.

Entity matching should consider multiple signals:

- normalized name
- ORCID
- email
- institution
- publication overlap
- funding records
- public profile URL

Deduplication status should support:

```text
merged
probable_match
manual_review_required
distinct
```

When confidence is insufficient, require manual confirmation.

## Email Rules

Finding an email address and proving who owns it are separate tasks.

Email-to-person matching must preserve evidence:

```text
email
→ researcher
→ evidence
→ source
```

Never assign an email to a customer based only on weak proximity in HTML, PDF, or plain text.

Do not implement automatic email sending unless the user explicitly asks for the sending phase.

Any future email workflow must be:

```text
generate draft
→ human review
→ optional edit
→ explicit confirmation
→ send
→ record status
```

## Lead Scoring Rules

Default scoring dimensions:

- Funding Activity: 40%
- Research Direction Match: 30%
- Publication Recency: 20%
- Outsourcing Tendency: 10%

Default priority:

- High: score >= 80
- Medium: 50 <= score <= 79
- Low: score < 50

Weights and thresholds must be centralized and configurable.

Core numerical scoring should be deterministic and reproducible. LLMs may summarize evidence or explain scores, but they should not be the sole calculator of final numerical scores.

## LLM and Agent Rules

LLM features should be added only after the deterministic data pipeline is reliable.

When added, keep LLM code separate from:

- data-source clients
- normalization
- storage
- deterministic scoring

Use a provider abstraction rather than binding the project to one model vendor.

Conceptual interface:

```text
generate()
model_name
usage
estimated_cost
```

Track token usage and estimated cost for each AI call when LLM functionality is introduced.

## Testing Rules

Add or update tests for meaningful functional changes.

Data-source tests should cover:

- successful response
- empty response
- API error
- timeout
- retry behavior
- pagination when applicable
- normalization
- provenance fields

Tests must not call real external APIs unless a specific real-integration test is explicitly requested.

Before reporting a task complete:

- run relevant tests
- report modified files
- report test results
- report known limitations
- state whether real API testing was performed

## Documentation Rules

Update `README.md` when user-visible behavior changes.

Put detailed planning material in `docs/`, not in the README.

README should stay focused on:

- what the project is
- what is currently implemented
- what is not implemented
- how to install
- how to run
- how to test
- important safety/data rules

Use UTF-8 for Markdown files. Avoid rewriting Chinese Markdown through tools that corrupt encoding.

## Definition of Done

A module is not complete just because code runs.

A feature is complete only when it has:

```text
code
+ tests
+ error handling
+ provenance where applicable
+ configuration where required
+ documentation
+ realistic validation
```

If only mocked tests were run, say so clearly.
