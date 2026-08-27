# PubMed Stage 38: Data Source Adapter Specification

## Goal

Stage 38 defines how future data sources must be added to ScholarLead Agent.
This stage does not connect Europe PMC, bioRxiv, medRxiv, Semantic Scholar,
ORCID, institutional websites, or internal customer spreadsheets yet.

The goal is to prevent future sources from bypassing the current evidence-first
workflow.

## Required Flow

Every new source must follow:

```text
DataSource Client
-> Parser
-> Service
-> Tool Adapter
-> Unified Converter
-> UnifiedPaper / UnifiedResearcher / UnifiedOrganization / UnifiedFunding / UnifiedContact
-> EvidenceRecord
-> ResultPackage / API / Frontend / Email
```

## Required Components

Each future source must provide:

```text
DataSourceClient
DataSourceParser
DataSourceService
Tool Adapter
Unified Converter
Raw Storage
Processed Export
Mocked Tests
Run Report
Source Metadata
```

The executable checklist is in:

```text
src/scholarlead_agent/data_source_adapter.py
```

Main helpers:

```python
DataSourceAdapterSpec
validate_data_source_adapter_spec(...)
required_source_metadata_fields()
required_run_report_fields()
forbidden_bypasses()
```

## Required Source Metadata

Every external record must preserve:

```text
source_name
source_record_id
source_url
raw_file_path
collected_at
parser_version
converter_version
confidence
license_or_terms_note
```

Optional but recommended:

```text
rate_limit_note
access_restriction_note
```

The shared metadata model is:

```text
SourceMetadata
```

in:

```text
src/scholarlead_agent/unified_models.py
```

## Required Run Report Fields

Every source task must report:

```text
task_id
source_name
query
status
started_at
finished_at
raw_files
processed_files
record_count
errors
source_metadata
```

## Forbidden Bypasses

Future sources must not:

- call external APIs directly from Vue;
- call external APIs directly from FastAPI routes;
- call external APIs directly from Streamlit pages;
- skip raw data storage;
- skip EvidenceRecord generation;
- feed raw external fields directly into email generation;
- register an Agent Tool without mocked tests;
- use LLMs to guess missing emails;
- use LLMs to guess funding, identity, country, or affiliation facts.

## Testing Rules

Before a source can be registered as an Agent Tool, it must have mocked tests
for:

```text
client
parser
service
tool adapter
unified converter
raw storage or run report
```

Tests must not access the real network.

## Acceptance

- A reusable adapter specification module exists.
- Source metadata requirements are represented in code.
- Adapter validation is independently testable.
- The forbidden bypass rules are documented and test-covered.
- No new real data source is connected in this stage.
