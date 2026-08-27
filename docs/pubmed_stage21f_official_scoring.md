# PubMed Stage 21F: Official Four-Dimension Scoring Minimal Version

## Goal

Stage 21F adds a minimal official scoring module. It is separate from the older
PubMed-only temporary score.

The four dimensions and default weights are:

```text
funding_activity: 40%
research_direction_match: 30%
publication_recency: 20%
outsourcing_tendency: 10%
```

## New Module

```text
src/scholarlead_agent/official_scoring.py
```

Main entry points:

- `score_pubmed_lead_official_minimal`
- `score_researcher_official_minimal`
- `assign_official_priority`
- `OfficialScoringWeights`
- `PriorityThresholds`
- `DimensionScore`
- `OfficialScoreResult`

## Rules

- Funding activity can only use explicit funding records, such as NIH RePORTER.
- PubMed papers are not used to infer funding activity.
- Research direction can reuse deterministic keyword match scores.
- Publication recency uses publication year evidence.
- Outsourcing tendency remains missing unless explicit evidence is connected.
- If any dimension is missing, `official_total_score` is `null` and priority is
  `unscored`.
- Each scored dimension keeps evidence records.

## Not Included

- No LLM score calculation.
- No database storage.
- No email sending.
- No hidden funding inference.
- No automatic researcher/funding merge by name.

## Tests

Covered by:

```text
tests/test_official_scoring.py
```
