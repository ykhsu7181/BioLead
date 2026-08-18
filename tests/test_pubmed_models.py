from pathlib import Path

import pytest

from scholarlead_agent.pubmed_models import (
    PubMedSearchParams,
    validate_pubmed_search_inputs,
)


def test_validate_pubmed_search_inputs_returns_normalized_params() -> None:
    params = validate_pubmed_search_inputs(
        query="  single cell RNA sequencing  ",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=50,
        country=" us ",
        service_type=" scRNA-seq ",
        raw_dir="custom/raw",
        processed_dir="custom/processed",
    )

    assert params == PubMedSearchParams(
        query="single cell RNA sequencing",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=50,
        country="US",
        service_type="scRNA-seq",
        raw_dir=Path("custom/raw"),
        processed_dir=Path("custom/processed"),
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"query": "   "}, "query cannot be empty"),
        ({"from_date": "2024/01/01"}, "from_date must be in YYYY-MM-DD format"),
        ({"to_date": "2024/12/31"}, "to_date must be in YYYY-MM-DD format"),
        (
            {"from_date": "2024-12-31", "to_date": "2024-01-01"},
            "from_date must be earlier than or equal to to_date",
        ),
        ({"max_results": 0}, "max_results must be between 1 and 100"),
        ({"max_results": 101}, "max_results must be between 1 and 100"),
    ],
)
def test_validate_pubmed_search_inputs_rejects_invalid_values(
    overrides: dict[str, object],
    message: str,
) -> None:
    values = {
        "query": "genome assembly",
        "from_date": "2024-01-01",
        "to_date": "2024-12-31",
        "max_results": 10,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=message):
        validate_pubmed_search_inputs(**values)  # type: ignore[arg-type]


def test_validate_pubmed_search_inputs_uses_pubmed_default_dirs() -> None:
    params = validate_pubmed_search_inputs(
        query="genome assembly",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_results=10,
    )

    assert params.raw_dir == Path("data/raw/pubmed")
    assert params.processed_dir == Path("data/processed/pubmed")
    assert params.country is None
    assert params.service_type is None
