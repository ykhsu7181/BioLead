"""Company service catalog loading for ServiceMatcher."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_COMPANY_SERVICES_PATH = Path("data/config/company_services.csv")


@dataclass(frozen=True)
class CompanyService:
    """One company service entry from the external catalog."""

    catalog_version: str
    updated_at: str
    service_id: str
    service_name: str
    service_category: str
    description: str
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    synonyms: list[str] = field(default_factory=list)
    application_fields: list[str] = field(default_factory=list)
    supported_organisms: list[str] = field(default_factory=list)
    company_capability: str = ""
    selling_points: str = ""
    email_talking_points: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class CompanyServiceCatalog:
    """Loaded service catalog with version metadata."""

    catalog_version: str
    services: list[CompanyService]
    source_path: str


def load_company_service_catalog(
    path: Path | str = DEFAULT_COMPANY_SERVICES_PATH,
) -> CompanyServiceCatalog:
    """Load enabled and disabled company services from CSV."""

    source_path = Path(path)
    if not source_path.exists():
        raise FileNotFoundError(f"company service catalog not found: {source_path}")

    services: list[CompanyService] = []
    with source_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            service = _service_from_row(row)
            services.append(service)

    catalog_version = services[0].catalog_version if services else "unknown"
    return CompanyServiceCatalog(
        catalog_version=catalog_version,
        services=services,
        source_path=str(source_path),
    )


def _service_from_row(row: dict[str, str]) -> CompanyService:
    service_id = _required(row, "service_id")
    service_name = _required(row, "service_name")
    return CompanyService(
        catalog_version=_clean(row.get("catalog_version")) or "unknown",
        updated_at=_clean(row.get("updated_at")) or "",
        service_id=service_id,
        service_name=service_name,
        service_category=_clean(row.get("service_category")) or "",
        description=_clean(row.get("description")) or "",
        positive_keywords=_split_terms(row.get("positive_keywords")),
        negative_keywords=_split_terms(row.get("negative_keywords")),
        synonyms=_split_terms(row.get("synonyms")),
        application_fields=_split_terms(row.get("application_fields")),
        supported_organisms=_split_terms(row.get("supported_organisms")),
        company_capability=_clean(row.get("company_capability")) or "",
        selling_points=_clean(row.get("selling_points")) or "",
        email_talking_points=_clean(row.get("email_talking_points")) or "",
        enabled=_parse_bool(row.get("enabled"), default=True),
    )


def _required(row: dict[str, str], field_name: str) -> str:
    value = _clean(row.get(field_name))
    if not value:
        raise ValueError(f"{field_name} is required in company service catalog")
    return value


def _split_terms(value: str | None) -> list[str]:
    cleaned = _clean(value)
    if not cleaned:
        return []
    return [term.strip() for term in cleaned.split(";") if term.strip()]


def _parse_bool(value: str | None, *, default: bool) -> bool:
    cleaned = (_clean(value) or "").lower()
    if not cleaned:
        return default
    if cleaned in {"1", "true", "yes", "y", "enabled"}:
        return True
    if cleaned in {"0", "false", "no", "n", "disabled"}:
        return False
    return default


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None

