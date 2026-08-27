# PubMed Stage 34C: Vue Frontend Skeleton

## Goal

Stage 34C creates the first Vue frontend skeleton for ScholarLead Agent. It is
a migration starting point, not a finished product UI.

Streamlit remains the internal demo and debugging interface. Vue is prepared as
the future user-facing interface and talks to FastAPI only.

## Added Frontend

Directory:

```text
frontend/
```

Main files:

```text
frontend/package.json
frontend/index.html
frontend/vite.config.js
frontend/src/main.js
frontend/src/App.vue
frontend/src/api.js
frontend/src/styles.css
frontend/README.md
```

## Pages In The Skeleton

The first Vue shell includes five core views:

- Agent Conversation
- Task / Job Progress
- Customer List
- Customer Detail / Evidence
- Email Draft Review

The skeleton can call:

- `/api/health`
- `/api/leads`
- `/api/leads/{lead_id}`
- `/api/jobs`
- `/api/jobs/{job_id}`
- `/api/jobs/{job_id}/items`

Agent execution, batch draft generation, and real email sending remain server
workflow items for later stages.

## Run Backend

From the project root:

```powershell
$env:PYTHONPATH="src"
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

## Run Frontend

In another PowerShell window:

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

Default API base URL:

```text
http://127.0.0.1:8000
```

To override it:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
npm run dev
```

## Safety Rules

- No API key, SMTP password, OpenAI key, or `.env` value is included in frontend
  source code.
- The browser does not call PubMed, OpenAlex, Crossref, NIH RePORTER, LLM, SMTP,
  or SQLite directly.
- The email review page is a review placeholder in this stage and does not send
  real emails.

## Acceptance

- Vue project skeleton exists.
- Five core user-facing views are reachable.
- API base URL is configurable.
- Frontend secrets are not present.
- Existing Streamlit and CLI flows remain unchanged.
