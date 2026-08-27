from scholarlead_agent.nih_reporter_parser import (
    deduplicate_nih_funding_records,
    parse_nih_reporter_funding_records,
)


def test_parse_nih_reporter_funding_records_handles_core_fields() -> None:
    raw_response = {
        "results": [
            {
                "appl_id": 123456,
                "project_num": "R01CA123456",
                "project_title": "CRISPR imaging of cancer cells",
                "fiscal_year": 2026,
                "organization": {"org_name": "Stanford University"},
                "principal_investigators": [
                    {"first_name": "Lei S", "last_name": "Qi"},
                    {"full_name": "W E Moerner"},
                ],
                "award_amount": "$123,456",
                "project_start_date": "2025-07-01T00:00:00",
                "project_end_date": "2027-06-30T00:00:00",
                "agency_ic_admin": {"abbreviation": "NCI", "name": "National Cancer Institute"},
            }
        ]
    }

    records = parse_nih_reporter_funding_records(
        raw_response,
        raw_record_path="data/raw/nih_reporter/sample.json",
    )

    assert len(records) == 1
    assert records[0].source == "nih_reporter"
    assert records[0].grant_id == "R01CA123456"
    assert records[0].agency == "NCI"
    assert records[0].project_title == "CRISPR imaging of cancer cells"
    assert records[0].pi_name == "Lei S Qi; W E Moerner"
    assert records[0].institution == "Stanford University"
    assert records[0].fiscal_year == 2026
    assert records[0].amount == 123456.0
    assert records[0].source_url == "https://reporter.nih.gov/project-details/123456"
    assert records[0].raw_record_path == "data/raw/nih_reporter/sample.json"


def test_parse_nih_reporter_funding_records_handles_empty_response() -> None:
    assert parse_nih_reporter_funding_records({"results": []}) == []
    assert parse_nih_reporter_funding_records({"message": "no results"}) == []


def test_deduplicate_nih_funding_records_uses_grant_and_fiscal_year() -> None:
    raw_response = {
        "results": [
            {
                "project_num": "R01CA123456",
                "project_title": "Cancer imaging",
                "fiscal_year": 2026,
            },
            {
                "project_num": "R01CA123456",
                "project_title": "Cancer imaging duplicate",
                "fiscal_year": 2026,
            },
            {
                "project_num": "R01CA123456",
                "project_title": "Cancer imaging next year",
                "fiscal_year": 2027,
            },
        ]
    }
    records = parse_nih_reporter_funding_records(raw_response)

    deduplicated = deduplicate_nih_funding_records(records)

    assert [record.project_title for record in deduplicated] == [
        "Cancer imaging",
        "Cancer imaging next year",
    ]
