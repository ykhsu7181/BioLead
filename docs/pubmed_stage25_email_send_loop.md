# Stage 25: Controlled Email Send Loop

## Goal

Stage 25 adds the minimum controlled send loop around reviewed email drafts.

The implementation keeps the hard safety boundary:

- no SMTP configuration is included;
- no default real provider is configured;
- no Agent-accessible `send_email` tool is registered;
- the provider must be explicitly injected by trusted application code;
- permission checks must pass before the provider is called.

## Why This Is Not Automatic Sending

The project still lacks several real-world prerequisites:

- confirmed sender account;
- confirmed quota policy;
- legal / compliance wording;
- production approval workflow;
- provider failure and unsubscribe policy.

Therefore Stage 25 implements the code-level closed loop and test provider
interface, but does not make the Streamlit page or Agent send real email.

## Implemented

- `EmailSendRequest`
- `EmailProvider` protocol
- `EmailProviderResult`
- `EmailSendResult`
- `build_email_send_request`
- `send_reviewed_email`
- `email_send_result_to_dict`
- `email_send_logs` SQLite table
- `insert_email_send_log`
- audit record generation for:
  - `email_send_blocked`
  - `email_send_sent`
  - `email_send_failed`

## Send Flow

```text
reviewed email draft
-> PermissionPolicy check
-> provider presence check
-> single provider send call
-> send result
-> audit record
-> optional database send log
```

## Hard Blocks

The provider is not called when:

- draft is not approved;
- verified email is missing;
- sender account is not configured;
- quota is not configured or exceeded;
- real sending is disabled in policy;
- no provider is injected;
- subject or body is empty.

## Database

Stage 25 bumps the database schema version to `2` and adds:

```text
email_send_logs
```

The table stores blocked, sent, and failed attempts.

## Tests

Targeted tests:

```powershell
.\literature_env\Scripts\python.exe -m pytest tests\test_email_sending.py tests\test_email_review.py tests\test_database.py
```

Full regression:

```powershell
.\literature_env\Scripts\python.exe -m pytest
```

All provider behavior in tests uses a fake provider. Tests do not access SMTP,
email APIs, or the real network.

## Not Implemented

- SMTP provider;
- Gmail / Outlook / SendGrid / SES provider;
- Streamlit real send button;
- Agent `send_email` tool;
- bulk sending;
- unsubscribe handling;
- bounce tracking;
- production compliance workflow.

