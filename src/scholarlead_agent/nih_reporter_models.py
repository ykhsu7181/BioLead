"""Models and validation helpers for NIH RePORTER funding collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NIH_REPORTER_MAX_RESULTS_LIMIT = 20


@dataclass(frozen=True)
class NIHReporterSearchParams:
    """Validated parameters for one NIH RePORTER project search."""

    pi_name: str | None
    institution: str | None
    keyword: str | None
    from_year: int
    to_year: int
    max_results: int
    raw_dir: Path = Path("data/raw/nih_reporter")
    processed_dir: Path = Path("data/processed/nih_reporter")

    @property
    def query_label(self) -> str:
        """Return the stable label used in output filenames."""

        return self.pi_name or self.institution or self.keyword or "nih_reporter"


@dataclass(frozen=True)
class NIHFundingRecord:
    """Cleaned NIH RePORTER funding record used by downstream modules."""

    source: str
    grant_id: str
    agency: str
    project_title: str
    pi_name: str
    institution: str
    fiscal_year: int | None
    project_start: str
    project_end: str
    amount: float | None
    source_url: str
    raw_record_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the funding record to a serializable dictionary."""

        return asdict(self)


def validate_nih_reporter_search_inputs(
    *,
    pi_name: str | None = None,
    institution: str | None = None,
    keyword: str | None = None,
    from_year: int,
    to_year: int,
    max_results: int,
    raw_dir: Path | str = Path("data/raw/nih_reporter"),
    processed_dir: Path | str = Path("data/processed/nih_reporter"),
) -> NIHReporterSearchParams:
    """Validate user inputs for one NIH RePORTER project query."""

    if isinstance(from_year, bool) or not isinstance(from_year, int):
        raise ValueError("from_year must be an integer")
    if isinstance(to_year, bool) or not isinstance(to_year, int):
        raise ValueError("to_year must be an integer")
    if from_year < 1900 or to_year < 1900:
        raise ValueError("from_year and to_year must be valid fiscal years")
    if from_year > to_year:
        raise ValueError("from_year must be earlier than or equal to to_year")

    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer")
    if max_results < 1 or max_results > NIH_REPORTER_MAX_RESULTS_LIMIT:
        raise ValueError(
            f"max_results must be between 1 and {NIH_REPORTER_MAX_RESULTS_LIMIT}"
        )

    normalized_pi_name = _normalize_optional_text(pi_name)
    normalized_institution = _normalize_optional_text(institution)
    normalized_keyword = _normalize_optional_text(keyword)
    if (
        normalized_pi_name is None
        and normalized_institution is None
        and normalized_keyword is None
    ):
        raise ValueError("pi_name, institution, or keyword is required")

    return NIHReporterSearchParams(
        pi_name=normalized_pi_name,
        institution=normalized_institution,
        keyword=normalized_keyword,
        from_year=from_year,
        to_year=to_year,
        max_results=max_results,
        raw_dir=Path(raw_dir),
        processed_dir=Path(processed_dir),
    )


def nih_funding_records_to_dicts(
    records: list[NIHFundingRecord],
) -> list[dict[str, Any]]:
    """Convert NIH funding records to dictionaries."""

    return [record.to_dict() for record in records]


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None
