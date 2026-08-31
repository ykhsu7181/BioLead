# Email-E5: Academic Cold Email Prompt v2

## Scope

This stage upgrades the email-draft prompt only. It keeps the existing human review, permission, controlled sending, batch drafting, API, Vue, and database boundaries unchanged.

## Completed

- Added `academic_cold_email_v2` as the default prompt version in `EmailDraftInput` evidence.
- Replaced the general email prompt with an Academic Cold Email Prompt v2.
- Required a JSON response with exactly `subject` and `body` string fields.
- Required a concise three-paragraph English email:
  - a concrete paper observation;
  - evidence-constrained sender relevance;
  - a low-pressure academic-exchange invitation.
- Added a conservative greeting: `Dear [Full Name],` when no explicit title evidence is available.
- Added fixed-signature instructions derived from `SenderProfile`.
- Added `sender_intro_style` to the fixed sender profile. Supported values are `i_lead` and `organization_representative`.
- `I lead` is only permitted when the fixed sender profile explicitly sets `sender_intro_style` to `i_lead`.

## Evidence Isolation

The model receives a narrower evidence package than the full audit/export evidence.

- In `capability_grounded` mode, the prompt may use only deterministic `candidate_capabilities`; it must not invent or enumerate a product list.
- In `paper_only` mode, service-match fields and all capability details are removed from model-visible evidence. The prompt permits only general academic interest grounded in the paper evidence.
- No full text, inferred findings, funding claims, customer needs, or unprovided author facts are allowed.

## Deferred to Email-E6

- Structured draft quality report.
- Failure classification.
- One bounded regeneration attempt for a quality failure.
- Enforcement that invalid model JSON is a quality failure rather than a legacy parser fallback.

## Tests

- Prompt contains Academic Cold Email v2 structure and a safe greeting.
- Prompt receives `i_lead` only as an explicit sender-profile setting.
- Paper-only prompt removes service and capability claims.
- Unsupported sender introduction styles are rejected.
- Existing draft, draft-tool, batch-draft, and sender-profile regression tests pass.

Focused result: `28 passed`.
