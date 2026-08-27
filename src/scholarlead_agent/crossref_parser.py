"""Parser and normalizer for Crossref Works responses."""

from __future__ import annotations

import re
from typing import Any

from scholarlead_agent.crossref_models import CrossrefWork, normalize_crossref_doi


def parse_crossref_works(
    raw_response: dict[str, Any],
    *,
    raw_record_path: str | None = None,
) -> list[CrossrefWork]:
    """Parse a Crossref Works response into normalized work records."""

    message = raw_response.get("message")
    if not isinstance(message, dict):
        return []

    items = message.get("items")
    if isinstance(items, list):
        return [
            _parse_crossref_work(item, raw_record_path=raw_record_path)
            for item in items
            if isinstance(item, dict)
        ]

    if "DOI" in message or "title" in message:
        return [_parse_crossref_work(message, raw_record_path=raw_record_path)]

    return []


def deduplicate_crossref_works(works: list[CrossrefWork]) -> list[CrossrefWork]:
    """Deduplicate Crossref works by DOI first, then weak title/year/author key."""

    seen_keys: set[tuple[str, str]] = set()
    deduplicated: list[CrossrefWork] = []

    for work in works:
        if work.doi:
            key = ("doi", work.doi)
        else:
            key = (
                "weak",
                "|".join(
                    [
                        _normalize_key_text(work.title),
                        str(work.publication_year or ""),
                        _normalize_key_text(work.authors[0] if work.authors else ""),
                    ]
                ),
            )

        if key[1] and key in seen_keys:
            continue
        seen_keys.add(key)
        deduplicated.append(work)

    return deduplicated


def _parse_crossref_work(
    item: dict[str, Any],
    *,
    raw_record_path: str | None,
) -> CrossrefWork:
    doi = normalize_crossref_doi(_optional_string(item.get("DOI")))
    title = _first_text(item.get("title"))
    publication_date, publication_year = _extract_publication_date(item)

    return CrossrefWork(
        source="crossref",
        crossref_id=doi or _optional_string(item.get("URL")) or title,
        doi=doi,
        title=title,
        abstract=_strip_markup(_optional_string(item.get("abstract")) or ""),
        journal=_first_text(item.get("container-title")),
        publisher=_optional_string(item.get("publisher")) or "",
        publication_date=publication_date,
        publication_year=publication_year,
        authors=_extract_authors(item.get("author")),
        funder_names=_extract_funders(item.get("funder")),
        reference_count=_optional_int(item.get("reference-count")),
        is_referenced_by_count=_optional_int(item.get("is-referenced-by-count")),
        source_url=_build_source_url(doi, _optional_string(item.get("URL"))),
        raw_record_path=raw_record_path,
    )


def _extract_publication_date(item: dict[str, Any]) -> tuple[str, int | None]:
    for field_name in ("published-print", "published-online", "created", "deposited"):
        date_value = _date_parts_to_date(item.get(field_name))
        if date_value:
            year = _safe_year(date_value)
            return date_value, year
    return "", None


def _date_parts_to_date(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts:
        return ""
    first = date_parts[0]
    if not isinstance(first, list) or not first:
        return ""

    parts = [part for part in first[:3] if isinstance(part, int)]
    if not parts:
        return ""
    year = f"{parts[0]:04d}"
    if len(parts) == 1:
        return year
    month = f"{parts[1]:02d}"
    if len(parts) == 2:
        return f"{year}-{month}"
    day = f"{parts[2]:02d}"
    return f"{year}-{month}-{day}"


def _safe_year(value: str) -> int | None:
    try:
        return int(value[:4])
    except ValueError:
        return None


def _extract_authors(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        full_name = _format_author_name(author)
        if full_name:
            authors.append(full_name)
    return _unique_preserve_order(authors)


def _format_author_name(author: dict[str, Any]) -> str:
    given = _optional_string(author.get("given")) or ""
    family = _optional_string(author.get("family")) or ""
    literal = _optional_string(author.get("name")) or ""
    full_name = " ".join(part for part in [given.strip(), family.strip()] if part)
    return full_name or literal.strip()


def _extract_funders(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    names: list[str] = []
    for funder in value:
        if not isinstance(funder, dict):
            continue
        name = _optional_string(funder.get("name"))
        if name:
            names.append(name.strip())
    return _unique_preserve_order(names)


def _build_source_url(doi: str | None, raw_url: str | None) -> str:
    if raw_url:
        return raw_url
    if doi:
        return f"https://doi.org/{doi}"
    return ""


def _first_text(value: Any) -> str:
    if isinstance(value, list) and value:
        first = value[0]
        return str(first).strip() if first is not None else ""
    if isinstance(value, str):
        return value.strip()
    return ""


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _strip_markup(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value).strip()


def _normalize_key_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
