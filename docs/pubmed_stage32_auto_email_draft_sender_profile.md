# PubMed Stage 32: Auto Email Draft Completion and Fixed SenderProfile

## Scope

This stage implements automatic email draft evidence completion:

```text
PubMed Lead
-> ServiceMatcher
-> matched company service
-> fixed SenderProfile
-> human-review email draft
```

It does not implement batch drafting, batch sending, or any new email sending permission bypass.

## Files

- `data/config/sender_profile.json`
  - Non-secret fixed sender identity.
  - Contains sender name, title, organization, sender email, signature, and profile version.

- `src/scholarlead_agent/sender_profile.py`
  - Loads and validates `SenderProfile`.
  - Converts it to evidence-safe metadata.

- `src/scholarlead_agent/services/email_draft_service.py`
  - Adds `build_auto_email_draft_input_from_lead`.
  - Adds `EmailDraftService.generate_for_lead`.
  - Calls ServiceMatcher before model generation.

- `src/scholarlead_agent/ai/email_drafts.py`
  - Extends draft evidence with matched service and sender profile metadata.

- `src/scholarlead_agent/ui/streamlit_app.py`
  - Email draft panel no longer asks users to manually fill sender name, sender title, organization, or target service type.
  - Shows matched service and fixed sender profile after draft generation.

## SenderProfile

The first version is stored in:

```text
data/config/sender_profile.json
```

Example fields:

```json
{
  "profile_version": "2026-08-26-v1",
  "sender_name": "ScholarLead Agent",
  "sender_title": "Research Partnership Team",
  "sender_organization": "ScholarLead Agent",
  "sender_email": "agent_test@yeah.net",
  "signature": "Best regards,\nScholarLead Agent"
}
```

This file must not contain SMTP passwords, authorization codes, API keys, or tokens.

## Service Matching

The draft generator uses:

```text
data/config/company_services.csv
```

If an enabled service is matched, the draft evidence includes:

- service id
- service name
- match score
- match reason
- matched terms
- catalog version
- matcher version

If no enabled service is matched, automatic draft generation is blocked before any model call.

If the match status is `needs_review`, a warning is added to the draft evidence so the reviewer can check the service fit manually.

## Safety

- No email is sent by this stage.
- The existing human review and test-send flow remains unchanged.
- The model sees only evidence-safe sender profile data.
- The model is not allowed to invent services, emails, funding, affiliations, or claims.

## Validation

Run:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_sender_profile.py tests\test_service_catalog.py tests\test_service_matching.py tests\test_email_drafts.py tests\test_email_draft_tool.py tests\test_pubmed_ui.py
```

Then run full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```
