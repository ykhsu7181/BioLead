# Stage 23: Email Review And Send Permission Design

## Goal

Stage 23 adds the review and permission boundary for email drafts.

This stage still does not send real email. It only defines the states, policy
checks, and audit records required before a future sending module can exist.

## Implemented

- Email draft review decision model.
- Review status transitions:
  - `review_pending`
  - `review_approved`
  - `review_rejected`
  - `changes_requested`
- `PermissionPolicy` for future send checks.
- `SendPermissionResult` with `allowed`, `status`, `blockers`, and `warnings`.
- Email audit record model.
- JSONL append helper for audit records.
- Streamlit email draft panel review controls.
- Tests proving the default policy blocks sending.
- Tests proving a fully enabled test policy can allow a reviewed draft.
- Tests proving the default Agent registry still has no `send_email` tool.

## Review Flow

```text
generate draft
-> human review
-> approve / reject / request changes
-> permission check
-> audit record
```

The current system stops at permission design. There is no SMTP call and no
send provider integration.

## Permission Rules

The default policy blocks sending because:

- real email sending is disabled;
- no sender account is configured;
- no daily quota is configured.

Future real sending must also require:

- `draft_status = review_approved`;
- non-empty human reviewer;
- review timestamp;
- verified email;
- allowed email status;
- non-empty subject;
- non-empty body;
- quota available.

## Audit Records

Audit records include:

- event id;
- event type;
- lead id;
- actor;
- timestamp;
- status before and after;
- permission result;
- permission blockers;
- note;
- safe metadata.

Audit records intentionally omit email body, subject, API keys, passwords,
tokens, and secrets from metadata.

Default audit directory:

```text
data/processed/email_audit
```

Environment variable:

```text
EMAIL_AUDIT_DIR=data/processed/email_audit
```

When a review decision is saved in Streamlit, one JSONL audit record is appended
to:

```text
data/processed/email_audit/email_audit.jsonl
```

## New Files

```text
src/scholarlead_agent/email_review.py
tests/test_email_review.py
docs/pubmed_stage23_email_review_permission.md
```

## Updated Files

```text
src/scholarlead_agent/config.py
.env.example
tests/test_llm_adapter.py
README.md
```

## Not Implemented

- real email sending;
- SMTP configuration;
- send provider integration;
- bulk sending;
- automatic approval;
- Agent-accessible `send_email` tool;
- database-backed review workspace.

## Tests

Run:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_email_review.py tests\test_email_drafts.py tests\test_email_draft_tool.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
