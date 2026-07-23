# Codex Project Instructions

## General rules

- Use Python 3.11 or newer.
- Use clear, beginner-friendly code.
- Add type hints to public functions.
- Keep functions small and testable.
- Add comments only where the logic is not obvious.
- Add or update tests for every functional change.
- Run tests before completing a task.

## Security rules

- Never write passwords or API keys directly in code.
- Read credentials from environment variables.
- Never commit the .env file.
- Do not create automatic email-sending functionality.
- Any future outbound email must require human approval.

## Data rules

- Prefer official APIs over web scraping.
- Preserve raw API responses before cleaning them.
- Record the source of extracted information.
- Do not guess missing author emails.
- Do not treat inferred information as confirmed fact.
- Deduplicate papers by DOI.
- If DOI is missing, use the OpenAlex ID.

## Architecture rules

- Keep API collection code separate from business logic.
- Keep LLM prompts separate from data collection.
- Keep email generation separate from email delivery.
- Use SQLite for the first prototype.