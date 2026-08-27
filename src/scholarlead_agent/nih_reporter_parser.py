"""Parser and normalizer for NIH RePORTER project responses."""

from __future__ import annotations

import re
from typing import Any

from scholarlead_agent.nih_reporter_models import NIHFundingRecord


def parse_nih_reporter_funding_records(
    raw_response: dict[str, Any],
    *,
    raw_record_path: str | None = None,
) -> list[NIHFundingRecord]:
    """Parse a NIH RePORTER search response into funding records."""

    items = raw_response.get("results")
    if not isinstance(items, list):
        return []

    return [
        _parse_project(item, raw_record_path=raw_record_path)
        for item in items
        if isinstance(item, dict)
    ]


def deduplicate_nih_funding_records(
    records: list[NIHFundingRecord],
) -> list[NIHFundingRecord]:
    """Deduplicate funding records by grant/fiscal year, then weak identity."""

    seen_keys: set[tuple[str, str]] = set()
    deduplicated: list[NIHFundingRecord] = []

    for record in records:
        if record.grant_id:
            key = ("grant", f"{record.grant_id}|{record.fiscal_year or ''}")
        else:
            key = (
                "weak",
                "|".join(
                    [
                        _normalize_key_text(record.project_title),
                        _normalize_key_text(record.pi_name),
                        _normalize_key_text(record.institution),
                        str(record.fiscal_year or ""),
                    ]
                ),
            )
        if key[1] and key in seen_keys:
            continue
        seen_keys.add(key)
        deduplicated.append(record)

    return deduplicated


def _parse_project(
    item: dict[str, Any],
    *,
    raw_record_path: str | None,
) -> NIHFundingRecord:
    appl_id = _optional_string(_get_any(item, "appl_id", "ApplId"))
    grant_id = (
        _optional_string(_get_any(item, "project_num", "ProjectNum"))
        or _optional_string(_get_any(item, "core_project_num", "CoreProjectNum"))
        or appl_id
        or ""
    )
    return NIHFundingRecord(
        source="nih_reporter",
        grant_id=grant_id,
        agency=_extract_agency(_get_any(item, "agency_ic_admin", "AgencyIcAdmin")),
        project_title=_optional_string(
            _get_any(item, "project_title", "ProjectTitle", "title", "Title")
        )
        or "",
        pi_name=_extract_pi_names(
            _get_any(item, "principal_investigators", "PrincipalInvestigators")
        ),
        institution=_extract_institution(
            _get_any(item, "organization", "Organization")
        ),
        fiscal_year=_optional_int(_get_any(item, "fiscal_year", "FiscalYear")),
        project_start=_optional_string(
            _get_any(item, "project_start_date", "ProjectStartDate")
        )
        or "",
        project_end=_optional_string(
            _get_any(item, "project_end_date", "ProjectEndDate")
        )
        or "",
        amount=_optional_float(
            _get_any(item, "award_amount", "AwardAmount", "total_cost", "TotalCost")
        ),
        source_url=_build_source_url(
            appl_id,
            _optional_string(
                _get_any(item, "project_detail_url", "ProjectDetailUrl", "url", "URL")
            ),
        ),
        raw_record_path=raw_record_path,
    )


def _extract_agency(value: Any) -> str:
    if isinstance(value, dict):
        return (
            _optional_string(value.get("abbreviation"))
            or _optional_string(value.get("code"))
            or _optional_string(value.get("name"))
            or "NIH"
        )
    if isinstance(value, list):
        names = [_extract_agency(item) for item in value]
        return "; ".join(_unique([name for name in names if name])) or "NIH"
    return _optional_string(value) or "NIH"


def _extract_pi_names(value: Any) -> str:
    if not isinstance(value, list):
        return _optional_string(value) or ""

    names: list[str] = []
    for person in value:
        if not isinstance(person, dict):
            continue
        full_name = (
            _optional_string(person.get("full_name"))
            or _optional_string(person.get("name"))
            or _optional_string(person.get("pi_name"))
        )
        if full_name:
            names.append(full_name.strip())
            continue
        first_name = _optional_string(person.get("first_name")) or ""
        last_name = _optional_string(person.get("last_name")) or ""
        built_name = " ".join(part for part in [first_name.strip(), last_name.strip()] if part)
        if built_name:
            names.append(built_name)
    return "; ".join(_unique(names))


def _extract_institution(value: Any) -> str:
    if isinstance(value, dict):
        return (
            _optional_string(value.get("org_name"))
            or _optional_string(value.get("name"))
            or _optional_string(value.get("organization_name"))
            or ""
        )
    return _optional_string(value) or ""


def _build_source_url(appl_id: str | None, raw_url: str | None) -> str:
    if raw_url:
        return raw_url
    if appl_id:
        return f"https://reporter.nih.gov/project-details/{appl_id}"
    return "https://reporter.nih.gov/"


def _get_any(item: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in item:
            return item[name]
    return None


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    if isinstance(value, int):
        return str(value)
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[$,]", "", value.strip())
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _normalize_key_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values
