# Git Commit Log

This file records project git commits, timestamps, and the main content of each commit.

## Existing History

| Commit | Time | Summary |
| --- | --- | --- |
| `c706b65` | 2026-07-23 11:55:38 +08:00 | Initialize literature agent |
| `47a0fcb` | 2026-07-23 15:21:56 +08:00 | Add OpenAlex paper collector |

## 2026-08-18

### 2026-08-18 16:54:01 +08:00

Planned commit message:

```text
Implement PubMed first-round workflow
```

Main content:

- Rename project package direction from `literature_agent` to `scholarlead_agent`.
- Add PubMed ESearch / EFetch client with retry, timeout, and User-Agent support.
- Add PubMed raw response storage for ESearch JSON, EFetch XML, and request metadata.
- Add PubMed XML parser for papers, authors, affiliations, abstracts, DOI, MeSH, and keywords.
- Add PubMed paper deduplication by DOI first, then PMID.
- Add email evidence extraction from PubMed affiliation text only.
- Add PubMed lead generation, lead deduplication, and manual review markers.
- Add affiliation-based institution and country identification.
- Add keyword matching and service type tagging.
- Add PubMed-only temporary scoring and priority assignment.
- Add processed papers/leads JSON and CSV export.
- Add Run Report generation.
- Add reusable PubMed service entry point and end-to-end CLI orchestration.
- Update README, README_cn, AGENTS, `.env.example`, and PubMed stage docs.
- Add pytest coverage for PubMed client, parser, leads, scoring, storage, and CLI.

Verification:

```text
.\literature_env\Scripts\python.exe -m pytest
112 passed
```

Notes:

- Generated files under `data/raw/pubmed` and `data/processed/pubmed` are ignored except `.gitkeep`.
- No LLM, Agent Loop, database, Streamlit UI, or email sending is included in this commit.

## 2026-08-20

### 2026-08-20 14:43:23 +08:00

Planned commit message:

```text
Add PubMed Streamlit UI and email extraction fix
```

Main content:

- Add PubMed stage 17 full regression report.
- Add lightweight Streamlit UI for PubMed first-round search, result display, lead detail view, run report view, and file downloads.
- Add UI helper tests for summary, paper rows, lead rows, and lead filters.
- Add Streamlit dependency and README / README_cn launch instructions.
- Fix PubMed affiliation email extraction when an email is followed by a sentence-final period.
- Add regression test for sentence-final email extraction.

Verification:

```text
.\literature_env\Scripts\python.exe -m pytest
117 passed
```

Notes:

- Streamlit UI reuses the existing PubMed service entry point.
- No LLM, Agent Loop, database, or real email sending is added.
- The local requirement PDF is not included in this commit.
