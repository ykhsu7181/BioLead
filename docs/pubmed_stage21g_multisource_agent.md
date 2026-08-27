# PubMed Stage 21G: Multi-Source Agent Scheduling

## Goal

Stage 21G lets the Agent coordinate the existing data-source tools through the
ToolRegistry:

```text
search_pubmed
search_crossref
search_openalex
search_funding
```

The Agent Loop itself still does not hard-code tool behavior.

## Implemented

- The system prompt now explains when to use each data-source tool.
- It tells the Agent to report which sources were used.
- It keeps the boundaries clear: Crossref and OpenAlex are enrichment sources,
  NIH RePORTER is explicit NIH funding evidence, and PubMed remains the main
  lead-discovery path.
- `extract_tool_sources` can read tool result messages and summarize used data
  sources.
- Fake Model tests confirm multiple tools can be called in one Agent run.

## Boundaries

- No Planner module yet.
- No real model smoke test is required for pytest.
- No database.
- No real email sending.
- No direct LLM scoring.

## Tests

Covered by:

```text
tests/test_agent_runtime.py
tests/test_agent_loop.py
```
