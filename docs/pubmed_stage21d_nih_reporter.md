# PubMed Stage 21D: NIH RePORTER Funding Source

## Goal

Stage 21D adds NIH RePORTER as a funding evidence source for ScholarLead Agent.

This stage only collects and normalizes NIH project funding records. It does not
generate leads, merge researchers, run official four-dimension scoring, draft
new outreach logic, or send email.

## New Entry Points

- `NIHReporterClient.search_projects`
- `run_nih_reporter_search`
- `search_funding` Agent Tool
- `nih_funding_record_to_unified_funding`

## Inputs

- `pi_name`
- `institution`
- `keyword`
- `from_year`
- `to_year`
- `max_results`

At least one of `pi_name`, `institution`, or `keyword` is required. The first
version limits `max_results` to 20.

## Outputs

Processed funding records include:

- `grant_id`
- `agency`
- `project_title`
- `pi_name`
- `institution`
- `fiscal_year`
- `project_start`
- `project_end`
- `amount`
- `source_url`
- `raw_record_path`

Raw NIH RePORTER API responses are saved under `data/raw/nih_reporter/`.
Cleaned JSON, CSV, and run reports are saved under `data/processed/nih_reporter/`.

## Boundaries

- NIH RePORTER covers NIH-related funding only.
- Absence of NIH RePORTER results is not proof that a researcher has no funding.
- A paper author name is not enough to merge or confirm a PI.
- Funding records remain evidence, not formal scoring.
- Tests mock HTTP and do not access the real network.
