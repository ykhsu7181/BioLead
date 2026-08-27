# PubMed Stage 36: Batch Review And Controlled Send

## Goal

Stage 36 adds batch review and controlled batch send boundaries for approved
email drafts.

This stage still does not allow unattended Agent email sending. There is no
Agent `send_email` tool.

## Main Module

```text
src/scholarlead_agent/services/email_batch_service.py
```

Key functions:

```python
apply_batch_email_review(...)
send_batch_reviewed_emails(...)
count_email_sends_today(...)
```

## API Endpoints

```text
GET  /api/email-drafts
GET  /api/email-drafts/{draft_id}
POST /api/email-drafts/batch-review
POST /api/email-sends/batch-send
GET  /api/email-sends
```

## Batch Review

Request:

```json
{
  "draft_ids": ["draft-lead-1"],
  "reviewer": "Reviewer",
  "decision": "approve",
  "comments": "Reviewed."
}
```

Supported decisions:

```text
approve
reject
request_changes
```

Review results are saved to:

```text
email_drafts
email_reviews
```

## Batch Send Modes

```text
permission_check
test_recipient
real_recipient
```

`permission_check` is the safest default. It evaluates permission and writes a
blocked send log with `permission_check_only`; no provider is called.

`test_recipient` sends to the configured test recipient only, using the existing
Stage 28 SMTP test-send logic.

`real_recipient` sends to the draft's verified recipient only when all
permission checks pass and an email provider is configured by trusted backend
code.

## Permission Checks

The send boundary checks:

- real email sending is enabled;
- sender account is configured;
- draft is approved by a human reviewer;
- reviewer and reviewed timestamp exist;
- verified email exists;
- email status is allowed;
- subject and body exist;
- daily quota is not exceeded;
- provider is available for real send.

Failed checks do not call the provider. They are recorded as blocked logs.

## Frontend

The Vue skeleton now includes basic controls for:

- listing drafts;
- selecting drafts;
- approving selected drafts;
- running selected drafts through the send boundary;
- viewing send logs.

## Acceptance

- Batch review updates draft status and writes audit records.
- Batch send writes logs for sent, failed, and blocked outcomes.
- Permission-check mode never calls an email provider.
- Tests use fake providers and do not send real email.
- Existing single-email send boundary remains unchanged.
