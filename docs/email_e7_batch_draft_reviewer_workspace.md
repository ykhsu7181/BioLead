# Email-E7: Batch Draft v2 and Reviewer Workspace

## Scope

This stage improves batch draft handling and reviewer visibility. It does not add autonomous sending or a new capability-match review gate.

## Completed

- Added a read-only Reviewer Workspace projection for each persisted email draft.
- The API now includes `reviewer_workspace` on email-draft list and detail responses.
- Reviewer Workspace groups existing evidence into:
  - paper title, abstract preview, keywords, identifiers, and source references;
  - capability match status and matched capability items;
  - quality report;
  - prompt, matcher, catalog, sender-profile, draft-mode, and draft-version metadata;
  - draft warnings.
- Repeated batch generation now creates a new draft version instead of overwriting the previous record:
  - first: `draft-{lead_id}` / `v1`;
  - next: `draft-{lead_id}-v2` / `v2`;
  - later versions continue incrementally and reference `supersedes_draft_id`.
- Vue email-draft page now has:
  - a batch-draft generation form using task ID and item limit;
  - quality status in the draft table;
  - a reviewer detail panel with paper evidence, capability match, quality report, version data, warnings, and draft body.
- Result Package E6 quality columns remain available for export.
- Sending permission now blocks a draft whose persisted quality report has `status=fail`, even if a later review state is changed to approved.

## Boundaries

- Drafts still default to human review.
- Capability matching remains informational; `matched`, `partial_match`, and `no_match` do not add another manual gate.
- Batch generation never sends email.
- Batch send remains controlled by the existing review, permission, recipient, quota, and provider rules.
- This stage preserves generated versions. Full editable revision history and an explicit reviewer-triggered regeneration action are deferred rather than silently overwriting prior drafts.

## Tests

- Batch generation persists drafts and job records.
- Repeated batch generation creates `v2` rather than overwriting `v1`.
- Reviewer Workspace projects evidence, capability items, quality data, and versions.
- Email-draft API exposes the Reviewer Workspace payload.
- Vue source exposes batch generation and Reviewer Workspace controls.
- A quality-failed report blocks the provider even after approval.
- Vue production build succeeds.

Focused results:

- Python targeted tests: `37 passed, 1 warning`.
- Vue build: passed.

## Deferred to Email-E8

- A manually labeled benchmark of at least 20 papers.
- Prompt v1 versus Prompt v2 comparison.
- Controlled real end-to-end quality acceptance report.
