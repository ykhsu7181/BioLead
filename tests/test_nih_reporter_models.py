from pathlib import Path

import pytest

from scholarlead_agent.nih_reporter_models import (
    NIH_REPORTER_MAX_RESULTS_LIMIT,
    validate_nih_reporter_search_inputs,
)


def test_validate_nih_reporter_inputs_accepts_pi_institution_keyword(
    tmp_path: Path,
) -> None:
    params = validate_nih_reporter_search_inputs(
        pi_name="  Lei   S Qi ",
        institution=" Stanford University ",
        keyword="CRISPR imaging",
        from_year=2024,
        to_year=2026,
        max_results=5,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
    )

    assert params.pi_name == "Lei S Qi"
    assert params.institution == "Stanford University"
    assert params.keyword == "CRISPR imaging"
    assert params.query_label == "Lei S Qi"
    assert params.raw_dir == tmp_path / "raw"


def test_validate_nih_reporter_inputs_requires_search_text() -> None:
    with pytest.raises(ValueError, match="pi_name, institution, or keyword is required"):
        validate_nih_reporter_search_inputs(
            from_year=2024,
            to_year=2026,
            max_results=5,
        )


def test_validate_nih_reporter_inputs_rejects_invalid_year_range() -> None:
    with pytest.raises(ValueError, match="from_year must be earlier"):
        validate_nih_reporter_search_inputs(
            keyword="cancer",
            from_year=2026,
            to_year=2024,
            max_results=5,
        )


def test_validate_nih_reporter_inputs_limits_max_results() -> None:
    with pytest.raises(ValueError, match=f"between 1 and {NIH_REPORTER_MAX_RESULTS_LIMIT}"):
        validate_nih_reporter_search_inputs(
            keyword="cancer",
            from_year=2024,
            to_year=2026,
            max_results=NIH_REPORTER_MAX_RESULTS_LIMIT + 1,
        )
