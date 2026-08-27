# PubMed Stage 21E: Researcher / Organization / Evidence Resolution

## Goal

Stage 21E adds a conservative entity-resolution layer on top of existing
PubMed Lead evidence.

This stage moves from "one paper can create one Lead" toward reusable entities:

```text
Paper -> Author -> Researcher -> Organization -> Contact -> Evidence
```

The implementation is intentionally limited. It does not add a database, does
not run official scoring, does not send email, and does not connect funding to
researchers by name alone.

## New Module

```text
src/scholarlead_agent/entity_resolution.py
```

Main functions and objects:

- `resolve_pubmed_leads_to_entities`
- `detect_probable_researcher_matches`
- `EntityResolutionResult`
- `ResearcherMatchReview`

## Merge Rules

Researcher merging:

- Same verified email can be merged.
- Same email with conflicting names or conflicting countries is marked
  `manual_review_required`.
- Missing email means no automatic researcher merge.
- Same name alone is only a weak signal and is returned as `probable_match`.
- Same name plus same institution is still only `probable_match`, not a merge.

Organization merging:

- Same normalized institution name plus same known country can be merged.
- Unknown country is not forced into a guessed country.
- Original source Lead IDs are retained.

Contact creation:

- Only public verified email values already present on PubMed Leads are used.
- Missing emails are not guessed.

## Evidence

Each researcher, organization, and contact keeps field-level `EvidenceRecord`
objects. The stage also returns an aggregated evidence list for later reports
and scoring.

## Boundaries

- No ORCID resolution yet.
- No OpenAlex Author ID resolution yet.
- No NIH PI ID resolution yet.
- No formal multi-source lead merge yet.
- No official four-dimension scoring.
- No real email sending.

## Acceptance

- Same verified email can merge researchers.
- Same name alone does not auto-merge.
- Conflicts are marked for manual review.
- Organization records keep source evidence.
- Existing PubMed Lead export remains unchanged.
- Full pytest passes.
