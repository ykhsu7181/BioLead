"""Business rules for cleaning OpenAlex works."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any


MAX_RESULTS_LIMIT = 20


@dataclass(frozen=True)
class SearchParams:
    """Validated user search parameters."""

    query: str
    from_date: str
    to_date: str
    max_results: int


@dataclass(frozen=True)
class PaperRecord:
    """Cleaned paper record used by downstream modules."""

    openalex_id: str
    doi: str | None
    title: str
    abstract: str
    publication_date: str
    authors: list[str]
    institutions: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert the record to a serializable dictionary."""

        return asdict(self)


def validate_search_inputs(
    query: str,
    from_date: str,
    to_date: str,
    max_results: int,
) -> SearchParams:
    """Validate command-line search inputs."""

    clean_query = query.strip()
    if not clean_query:
        raise ValueError("query must not be empty")

    parsed_from_date = _parse_date(from_date, "from_date")
    parsed_to_date = _parse_date(to_date, "to_date")
    if parsed_from_date > parsed_to_date:
        raise ValueError("from_date must be earlier than or equal to to_date")

    if max_results < 1 or max_results > MAX_RESULTS_LIMIT:
        raise ValueError(f"max_results must be between 1 and {MAX_RESULTS_LIMIT}")

    return SearchParams(
        query=clean_query,
        from_date=parsed_from_date.isoformat(),
        to_date=parsed_to_date.isoformat(),
        max_results=max_results,
    )


def normalize_doi(doi: str | None) -> str | None:
    """Normalize a DOI value from OpenAlex."""

    if doi is None:
        return None

    value = doi.strip()
    prefix = "https://doi.org/"
    if value.lower().startswith(prefix):
        value = value[len(prefix) :]

    value = value.strip().lower()
    return value or None


def restore_abstract(
    abstract_inverted_index: dict[str, list[int]] | None,
) -> str:
    """Restore an abstract string from OpenAlex's inverted index format."""

    if not abstract_inverted_index:
        return ""

    position_to_word: dict[int, str] = {}
    for word, positions in abstract_inverted_index.items():
        for position in positions:
            position_to_word[position] = word

    return " ".join(
        word for _, word in sorted(position_to_word.items(), key=lambda item: item[0])
    )


def clean_works_response(raw_response: dict[str, Any]) -> list[PaperRecord]:
    """Clean and deduplicate works from a raw OpenAlex response."""

    records = [_extract_record(work) for work in raw_response.get("results", [])]
    return deduplicate_records(records)


def deduplicate_records(records: list[PaperRecord]) -> list[PaperRecord]:
    """Deduplicate records by DOI first, then OpenAlex ID."""

    seen_keys: set[tuple[str, str]] = set()
    deduplicated: list[PaperRecord] = []

    for record in records:
        if record.doi:
            key = ("doi", record.doi)
        else:
            key = ("openalex_id", record.openalex_id)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        deduplicated.append(record)

    return deduplicated


def records_to_dicts(records: list[PaperRecord]) -> list[dict[str, Any]]:
    """Convert a list of records to dictionaries."""

    return [record.to_dict() for record in records]


def _parse_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format") from error


def _extract_record(work: dict[str, Any]) -> PaperRecord:
    authorships = work.get("authorships") or []

    return PaperRecord(
        openalex_id=str(work.get("id") or ""),
        doi=normalize_doi(work.get("doi")),
        title=str(work.get("title") or work.get("display_name") or ""),
        abstract=restore_abstract(work.get("abstract_inverted_index")),
        publication_date=str(work.get("publication_date") or ""),
        authors=_extract_authors(authorships),
        institutions=_extract_institutions(authorships),
    )


def _extract_authors(authorships: list[dict[str, Any]]) -> list[str]:
    authors: list[str] = []
    for authorship in authorships:
        author_name = authorship.get("author", {}).get("display_name")
        if author_name:
            authors.append(str(author_name))
    return _unique_preserve_order(authors)


def _extract_institutions(authorships: list[dict[str, Any]]) -> list[str]:
    institutions: list[str] = []
    for authorship in authorships:
        for institution in authorship.get("institutions", []):
            institution_name = institution.get("display_name")
            if institution_name:
                institutions.append(str(institution_name))
    return _unique_preserve_order(institutions)


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values

