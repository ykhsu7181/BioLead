from pathlib import Path

import pytest

from scholarlead_agent.crossref_models import (
    CROSSREF_MAX_RESULTS_LIMIT,
    normalize_crossref_doi,
    validate_crossref_search_inputs,
)


def test_normalize_crossref_doi_removes_prefix_and_lowercases() -> None:
    assert (
        normalize_crossref_doi("  https://doi.org/10.1038/ABC123  ")
        == "10.1038/abc123"
    )
    assert normalize_crossref_doi("HTTP://doi.org/10.1000/XYZ") == "10.1000/xyz"
    assert normalize_crossref_doi("   ") is None
    assert normalize_crossref_doi(None) is None


def test_validate_crossref_search_inputs_prefers_doi_but_keeps_title_context() -> None:
    params = validate_crossref_search_inputs(
        doi="https://doi.org/10.1038/ABC123",
        title="A title",
        max_results=5,
        raw_dir="raw",
        processed_dir="processed",
    )

    assert params.doi == "10.1038/abc123"
    assert params.title == "A title"
    assert params.query_label == "10.1038/abc123"
    assert params.raw_dir == Path("raw")
    assert params.processed_dir == Path("processed")


def test_validate_crossref_search_inputs_accepts_title_only() -> None:
    params = validate_crossref_search_inputs(
        title="Single cell cancer",
        max_results=3,
    )

    assert params.doi is None
    assert params.title == "Single cell cancer"
    assert params.query_label == "Single cell cancer"


def test_validate_crossref_search_inputs_rejects_empty_query() -> None:
    with pytest.raises(ValueError, match="doi or title is required"):
        validate_crossref_search_inputs(doi="", title=" ", max_results=3)


def test_validate_crossref_search_inputs_rejects_invalid_max_results() -> None:
    with pytest.raises(ValueError, match=f"between 1 and {CROSSREF_MAX_RESULTS_LIMIT}"):
        validate_crossref_search_inputs(title="cancer", max_results=21)

    with pytest.raises(ValueError, match="max_results must be an integer"):
        validate_crossref_search_inputs(title="cancer", max_results=True)  # type: ignore[arg-type]
