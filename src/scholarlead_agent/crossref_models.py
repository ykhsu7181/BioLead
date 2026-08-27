"""Models and validation helpers for Crossref collection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CROSSREF_MAX_RESULTS_LIMIT = 20


@dataclass(frozen=True)
class CrossrefSearchParams:
    """Validated parameters for one Crossref query."""

    doi: str | None
    title: str | None
    max_results: int
    raw_dir: Path = Path("data/raw/crossref")
    processed_dir: Path = Path("data/processed/crossref")

    @property
    def query_label(self) -> str:
        """Return the stable label used in output filenames."""

        return self.doi or self.title or "crossref"


@dataclass(frozen=True)
class CrossrefWork:
    """Cleaned Crossref work metadata used by downstream modules."""

    source: str
    crossref_id: str
    doi: str | None
    title: str
    abstract: str
    journal: str
    publisher: str
    publication_date: str
    publication_year: int | None
    authors: list[str]
    funder_names: list[str]
    reference_count: int | None
    is_referenced_by_count: int | None
    source_url: str
    raw_record_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the work to a serializable dictionary."""

        return asdict(self)


def validate_crossref_search_inputs(
    *,
    doi: str | None = None,
    title: str | None = None,
    max_results: int,
    raw_dir: Path | str = Path("data/raw/crossref"),
    processed_dir: Path | str = Path("data/processed/crossref"),
) -> CrossrefSearchParams:
    """Validate user inputs for a Crossref query."""

    if isinstance(max_results, bool) or not isinstance(max_results, int):
        raise ValueError("max_results must be an integer")
    if max_results < 1 or max_results > CROSSREF_MAX_RESULTS_LIMIT:
        raise ValueError(
            f"max_results must be between 1 and {CROSSREF_MAX_RESULTS_LIMIT}"
        )

    normalized_doi = normalize_crossref_doi(doi)
    normalized_title = _normalize_optional_text(title)
    if normalized_doi is None and normalized_title is None:
        raise ValueError("doi or title is required")

    return CrossrefSearchParams(
        doi=normalized_doi,
        title=normalized_title,
        max_results=max_results,
        raw_dir=Path(raw_dir),
        processed_dir=Path(processed_dir),
    )


def normalize_crossref_doi(doi: str | None) -> str | None:
    """Normalize a DOI value for Crossref lookup and deduplication."""

    if doi is None:
        return None

    value = doi.strip()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break

    value = value.strip().lower()
    return value or None


def crossref_works_to_dicts(works: list[CrossrefWork]) -> list[dict[str, Any]]:
    """Convert Crossref works to dictionaries."""

    return [work.to_dict() for work in works]


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
