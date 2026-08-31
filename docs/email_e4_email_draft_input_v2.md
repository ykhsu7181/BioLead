# Email-E4: EmailDraftInput v2 and Paper-only Routing

## Scope

This stage extends the existing email draft evidence input. It does not change email sending, human review, FastAPI, Vue, database schema, or the LLM prompt policy.

## Completed Changes

- Added capability-match metadata to `EmailDraftInput`:
  - `capability_match_id`
  - `candidate_capabilities`
  - `capability_match_status`
  - `capability_profile_version`
  - `capability_matcher_version`
- Added paper-evidence fields:
  - `paper_evidence_summary`
  - `paper_evidence_source_refs`
  - `research_direction`
- Added `draft_mode` with three values:
  - `legacy_service_based`
  - `capability_grounded`
  - `paper_only`
- `target_service_type` is now optional for draft evidence. This preserves older service-based callers while allowing capability-only and paper-only routes.
- `build_auto_email_draft_input_from_lead` now runs ServiceMatcher and CapabilityMatcher independently.
- A missing service match no longer blocks draft-input construction.

## Automatic Routes

| Condition | Draft mode | Capability claim input |
| --- | --- | --- |
| One or more capability matches | `capability_grounded` | Only deterministic matched capabilities are retained. |
| No capability matches | `paper_only` | No sender capability is provided for a later prompt to claim. |
| Older direct caller with no capability result | `legacy_service_based` | Existing ServiceMatcher-based behavior remains compatible. |

`paper_only` is an evidence-routing decision only in this stage. Email-E5 must update the prompt so generated wording explicitly follows this route and never invents a sender capability.

## Validation Rules

- `no_match` must not contain candidate capabilities.
- `matched` and `partial_match` must contain at least one candidate capability.
- Candidate capabilities must be `CapabilityMatchItem` objects produced by the deterministic matcher.
- Raw paper and source evidence remains available through existing draft fields and `paper_evidence_source_refs`.

## Tests

- Service match plus capability match.
- Capability match when no company service matches.
- `paper_only` when no capability matches.
- Legacy input with an empty service type.
- Invalid `no_match` input containing a capability.
- Existing email draft, email tool, batch draft, catalog, and matcher tests.

Focused result: `34 passed`.

## Deferred

- Prompt v2 and paper-only wording policy.
- Draft quality validator.
- Capability-match persistence and historical version snapshots.
- API and Vue presentation of the new fields.
