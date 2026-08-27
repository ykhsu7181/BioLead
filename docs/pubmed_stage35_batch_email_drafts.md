# PubMed Stage 35: Batch Personalized Email Drafts

## Goal

Stage 35 adds the first controlled batch email draft workflow. It generates
review-pending drafts for existing PubMed leads by reusing:

- existing PubMed lead data;
- Company Service Catalog and ServiceMatcher;
- fixed SenderProfile;
- existing EmailDraftService;
- background job records.

It does not send emails.

## Main Module

```text
src/scholarlead_agent/services/email_batch_service.py
```

Key function:

```python
generate_batch_email_drafts(...)
```

## API Endpoint

```text
POST /api/email-drafts/batch-generate
```

Request:

```json
{
  "lead_ids": ["lead-1", "lead-2"],
  "task_id": null,
  "max_items": 10
}
```

Response includes:

```text
job_id
status
total_count
success_count
failed_count
blocked_count
draft_ids
errors
```

## Rules

- The function only reads leads already stored in the database.
- The model is called through `EmailDraftService`; tests use fake services.
- Drafts are saved to `email_drafts`.
- Job progress is saved to `jobs` and `job_items`.
- Missing service match or missing model result blocks the item instead of
  deleting existing data.
- Real sending is not part of this stage.

## Acceptance

- Batch draft generation exists as reusable service logic.
- API endpoint exists.
- Drafts are persisted.
- Job status is persisted.
- Tests do not access real network or real model APIs.
