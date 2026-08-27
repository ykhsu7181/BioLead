# ScholarLead Agent Frontend

This is the Stage 34C Vue skeleton. It is a user-interface starting point over
the FastAPI boundary and is not yet the full production frontend.

## Start

Backend from the project root:

```powershell
$env:PYTHONPATH="src"
.\literature_env\Scripts\python.exe -m uvicorn scholarlead_agent.api.app:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd "D:\ScholarLead Agent\frontend"
npm install
npm run dev
```

The default API base URL is `http://127.0.0.1:8000`. Override it with
`VITE_API_BASE_URL` when needed.

## Boundaries

The frontend calls FastAPI only. It does not access `.env`, SMTP, LLM providers,
PubMed, OpenAlex, Crossref, NIH RePORTER, or SQLite directly.
