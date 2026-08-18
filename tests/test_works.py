import pytest

from scholarlead_agent.works import (
    clean_works_response,
    normalize_doi,
    restore_abstract,
    validate_search_inputs,
)


def test_validate_search_inputs_accepts_valid_values() -> None:
    params = validate_search_inputs(" genome ", "2024-01-01", "2024-12-31", 20)

    assert params.query == "genome"
    assert params.from_date == "2024-01-01"
    assert params.to_date == "2024-12-31"
    assert params.max_results == 20


@pytest.mark.parametrize(
    ("query", "from_date", "to_date", "max_results"),
    [
        ("", "2024-01-01", "2024-12-31", 10),
        ("gene", "2024/01/01", "2024-12-31", 10),
        ("gene", "2024-12-31", "2024-01-01", 10),
        ("gene", "2024-01-01", "2024-12-31", 0),
        ("gene", "2024-01-01", "2024-12-31", 21),
    ],
)
def test_validate_search_inputs_rejects_invalid_values(
    query: str,
    from_date: str,
    to_date: str,
    max_results: int,
) -> None:
    with pytest.raises(ValueError):
        validate_search_inputs(query, from_date, to_date, max_results)


def test_normalize_doi_removes_prefix_and_lowercases() -> None:
    assert normalize_doi(" https://doi.org/10.1000/ABC ") == "10.1000/abc"
    assert normalize_doi(" 10.1000/XYZ ") == "10.1000/xyz"
    assert normalize_doi(None) is None


def test_restore_abstract_from_inverted_index() -> None:
    abstract = restore_abstract({"Genome": [0], "assembly": [1], "works.": [2]})

    assert abstract == "Genome assembly works."


def test_clean_works_response_extracts_fields_and_deduplicates() -> None:
    raw_response = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1000/ABC",
                "title": "First title",
                "abstract_inverted_index": {"A": [0], "paper": [1]},
                "publication_date": "2024-01-10",
                "authorships": [
                    {
                        "author": {"display_name": "Alice"},
                        "institutions": [{"display_name": "Institute A"}],
                    },
                    {
                        "author": {"display_name": "Bob"},
                        "institutions": [{"display_name": "Institute A"}],
                    },
                ],
            },
            {
                "id": "https://openalex.org/W2",
                "doi": "10.1000/abc",
                "title": "Duplicate DOI",
                "abstract_inverted_index": {},
                "publication_date": "2024-01-11",
                "authorships": [],
            },
            {
                "id": "https://openalex.org/W3",
                "doi": None,
                "display_name": "No DOI title",
                "abstract_inverted_index": {"No": [0], "doi": [1]},
                "publication_date": "2024-02-01",
                "authorships": [],
            },
            {
                "id": "https://openalex.org/W3",
                "doi": None,
                "title": "Duplicate OpenAlex ID",
                "abstract_inverted_index": {},
                "publication_date": "2024-02-02",
                "authorships": [],
            },
        ]
    }

    records = clean_works_response(raw_response)

    assert len(records) == 2
    first_record = records[0]
    assert first_record.openalex_id == "https://openalex.org/W1"
    assert first_record.doi == "10.1000/abc"
    assert first_record.title == "First title"
    assert first_record.abstract == "A paper"
    assert first_record.publication_date == "2024-01-10"
    assert first_record.authors == ["Alice", "Bob"]
    assert first_record.institutions == ["Institute A"]

    second_record = records[1]
    assert second_record.openalex_id == "https://openalex.org/W3"
    assert second_record.doi is None
    assert second_record.title == "No DOI title"

