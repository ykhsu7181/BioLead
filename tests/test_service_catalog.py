from pathlib import Path

import pytest

from scholarlead_agent.service_catalog import load_company_service_catalog


def test_load_company_service_catalog_from_csv(tmp_path: Path) -> None:
    catalog_path = tmp_path / "company_services.csv"
    catalog_path.write_text(
        "\n".join(
            [
                "catalog_version,updated_at,service_id,service_name,service_category,description,positive_keywords,negative_keywords,synonyms,application_fields,supported_organisms,company_capability,selling_points,email_talking_points,enabled",
                '2026-v1,2026-08-26,single_cell,Single Cell,sequencing,desc,"single-cell;cancer",,scRNA-seq,cancer,human,capability,selling,pitch,true',
            ]
        ),
        encoding="utf-8",
    )

    catalog = load_company_service_catalog(catalog_path)

    assert catalog.catalog_version == "2026-v1"
    assert catalog.source_path == str(catalog_path)
    assert len(catalog.services) == 1
    service = catalog.services[0]
    assert service.service_id == "single_cell"
    assert service.positive_keywords == ["single-cell", "cancer"]
    assert service.synonyms == ["scRNA-seq"]
    assert service.enabled is True


def test_load_company_service_catalog_requires_service_id(tmp_path: Path) -> None:
    catalog_path = tmp_path / "company_services.csv"
    catalog_path.write_text(
        "catalog_version,service_id,service_name\n2026-v1,,Missing ID\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="service_id is required"):
        load_company_service_catalog(catalog_path)


def test_load_company_service_catalog_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        load_company_service_catalog("missing-company-services.csv")
