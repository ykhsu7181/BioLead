import csv
import json
from pathlib import Path
from zipfile import ZipFile

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.result_package import (
    RESULT_PACKAGE_VERSION,
    SCORING_STATUS,
    SCORING_VERSION,
    build_result_package_from_pubmed_result,
)
from scholarlead_agent.services.pubmed_service import run_pubmed_search
from tests.test_pubmed_service import FakePubMedClient, make_params


def make_pubmed_result(tmp_path: Path):
    fixture_xml = Path("tests/fixtures/pubmed_efetch_response.xml").read_text(
        encoding="utf-8"
    )
    return run_pubmed_search(
        make_params(tmp_path),
        client=FakePubMedClient(efetch_xml=fixture_xml),
        timestamp="20260826_120000",
        task_id="pubmed-stage33",
        started_at="2026-08-26T12:00:00",
        finished_at="2026-08-26T12:00:01",
    )


def make_draft(lead_id: str, recipient_name: str, verified_email: str):
    return build_email_draft(
        evidence=EmailDraftInput(
            lead_id=lead_id,
            pi_full_name=recipient_name,
            verified_email=verified_email,
            email_status="verified_from_pubmed_affiliation",
            recent_publication_title="Single-cell RNA sequencing in cancer",
            abstract="Single-cell RNA sequencing was used in this cancer study.",
            source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            pmid="1",
            target_service_type="Single-cell RNA sequencing",
            matched_service_id="single_cell_rna_seq",
            matched_service_name="Single-cell RNA sequencing",
            service_match_score=0.76,
            service_match_reason="Matched single-cell and cancer terms.",
            service_matched_terms=["single-cell", "cancer"],
            service_match_status="matched",
            service_catalog_version="catalog-v1",
            service_matcher_version="rule-v1",
            sender_profile_version="sender-v1",
            sender_name="Alex Chen",
            sender_title="Research Partnership Manager",
            organization_name="Example Bio",
        ),
        subject="Question about your single-cell cancer study",
        body="Dear Dr. Example,\n\nI read your recent paper.\n\nBest regards,",
        model_name="fake-email-model",
        generated_at="2026-08-26T12:30:00",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def test_build_result_package_exports_expected_files_and_summary(tmp_path: Path) -> None:
    result = make_pubmed_result(tmp_path)

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
        created_at="2026-08-26T13:00:00",
    )

    assert package.package_id == "TASK_pubmed_stage33"
    assert package.status == "success"
    assert package.paths.package_dir.exists()
    assert package.paths.workbook_xlsx.exists()
    assert package.paths.customers_csv.exists()
    assert package.paths.papers_csv.exists()
    assert package.paths.funding_csv.exists()
    assert package.paths.evidence_csv.exists()
    assert package.paths.service_matches_csv.exists()
    assert package.paths.email_drafts_csv.exists()
    assert package.paths.task_summary_json.exists()

    summary = json.loads(package.paths.task_summary_json.read_text(encoding="utf-8"))
    assert summary["package_version"] == RESULT_PACKAGE_VERSION
    assert summary["task_id"] == "pubmed-stage33"
    assert summary["scoring_version"] == SCORING_VERSION
    assert summary["scoring_status"] == SCORING_STATUS
    assert summary["row_counts"]["customers"] == len(result.leads)


def test_result_package_customers_have_cross_sheet_ids_and_scoring_metadata(
    tmp_path: Path,
) -> None:
    result = make_pubmed_result(tmp_path)

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
    )
    customer_rows = read_csv(package.paths.customers_csv)

    assert customer_rows
    first = customer_rows[0]
    assert first["Task_ID"] == "pubmed-stage33"
    assert first["Researcher_ID"]
    assert first["Lead_ID"]
    assert first["Scoring_Version"] == SCORING_VERSION
    assert first["Scoring_Status"] == SCORING_STATUS
    assert first["Source_Links"].startswith("[")


def test_result_package_derives_service_match_rows_from_existing_email_drafts(
    tmp_path: Path,
) -> None:
    result = make_pubmed_result(tmp_path)
    lead = result.leads[0]
    draft = make_draft(
        lead.lead_id,
        recipient_name=lead.pi_full_name,
        verified_email=lead.verified_email or "missing",
    )

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
        email_drafts=[draft],
    )
    service_rows = read_csv(package.paths.service_matches_csv)
    draft_rows = read_csv(package.paths.email_drafts_csv)

    assert len(service_rows) == 1
    assert service_rows[0]["Lead_ID"] == lead.lead_id
    assert service_rows[0]["Service_ID"] == "single_cell_rna_seq"
    assert service_rows[0]["Match_Status"] == "matched"
    assert draft_rows[0]["Matched_Service_ID"] == "single_cell_rna_seq"
    assert draft_rows[0]["Researcher_ID"] == service_rows[0]["Researcher_ID"]


def test_result_package_workbook_contains_required_sheets(tmp_path: Path) -> None:
    result = make_pubmed_result(tmp_path)

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
    )

    with ZipFile(package.paths.workbook_xlsx) as workbook:
        names = set(workbook.namelist())
        workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")

    assert "xl/worksheets/sheet1.xml" in names
    assert "Customers" in workbook_xml
    assert "Service_Matches" in workbook_xml
    assert "Task_Summary" in workbook_xml


def test_result_package_does_not_create_service_matches_without_existing_evidence(
    tmp_path: Path,
) -> None:
    result = make_pubmed_result(tmp_path)

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
    )

    assert read_csv(package.paths.service_matches_csv) == []
