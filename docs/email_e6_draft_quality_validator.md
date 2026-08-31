# Email-E6: Draft Quality Validator

## Scope

This stage adds deterministic quality validation after model draft generation. It does not create an automated send path and does not alter existing human review or permission rules.

## Completed

- Added `email_draft_quality.py`, an independently callable validator with no model, SMTP, database, or network dependency.
- Added an exportable `EmailDraftQualityReport` with:
  - `status`: `pass`, `warning`, or `fail`;
  - failure reasons and non-blocking warnings;
  - word count, paragraph count, validator version, and check timestamp.
- Added hard failures for:
  - `empty_draft`;
  - `invalid_json`;
  - `missing_subject_or_body`;
  - `unsupported_capability_claim`;
  - `paper_only_contains_specific_capability_claim`;
  - `completely_missing_paper_grounding`.
- Added non-blocking warnings for word count, paragraph count, generic praise, collaboration language, and sales signals.
- `EmailDraftService` now retries once only when the report is `fail`, using the same evidence plus failure feedback.
- A second failure creates a retained `quality_failed` draft with its quality report and failure reasons. It remains `can_send=False`.
- Quality reports are included in draft evidence and added to Result Package email-draft exports.

## Safety Behavior

- `warning` does not add an extra manual-review gate.
- `quality_failed` does not call any email provider. Existing send permission already blocks non-approved drafts.
- No model call is made more than twice for a single generation request.
- No external network, SMTP, or LLM call is used by the validator itself.

## Tests

- Warning-only output remains usable.
- Paper-only drafts containing a specific service claim fail.
- Capability-grounded drafts containing an unsupported service claim fail.
- Missing paper grounding fails.
- Invalid JSON regenerates once.
- A repeated quality failure stops after the second model response.
- A quality-failed draft is blocked before provider invocation.
- Result package exports quality columns.

Focused result: `54 passed`.

## Deferred

- Dedicated database tables for historical quality reports.
- Reviewer UI presentation of quality reports and regeneration history.
- Benchmark evaluation on a manually labeled paper set.
