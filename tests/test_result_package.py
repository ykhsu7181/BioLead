import csv
import json
from pathlib import Path
from zipfile import ZipFile

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.database import (
    initialize_database,
    insert_email_draft,
    insert_email_review_record,
    insert_email_send_log,
    insert_pubmed_lead,
    insert_pubmed_paper,
    insert_task,
)
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    PermissionPolicy,
    apply_email_review_decision,
    build_email_audit_record,
    evaluate_send_permission,
)
from scholarlead_agent.email_sending import (
    EmailProviderResult,
    email_send_result_to_dict,
    send_reviewed_email,
)
from scholarlead_agent.result_package import (
    RESULT_PACKAGE_VERSION,
    SCORING_STATUS,
    SCORING_VERSION,
    build_result_package_from_database_task,
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


class FakeProvider:
    provider_name = "fake-provider"

    def send(self, request):
        return EmailProviderResult(
            success=True,
            provider=self.provider_name,
            provider_message_id="message-1",
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
    assert package.paths.email_reviews_csv.exists()
    assert package.paths.email_send_logs_csv.exists()
    assert package.paths.task_summary_json.exists()
    assert package.paths.readme_txt.exists()

    summary = json.loads(package.paths.task_summary_json.read_text(encoding="utf-8"))
    assert summary["package_version"] == RESULT_PACKAGE_VERSION
    assert summary["task_id"] == "pubmed-stage33"
    assert summary["scoring_version"] == SCORING_VERSION
    assert summary["scoring_status"] == SCORING_STATUS
    assert summary["row_counts"]["customers"] == len(result.leads)
    assert "email_reviews" in summary["row_counts"]
    assert "email_send_logs" in summary["row_counts"]


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
    assert "Quality_Status" in draft_rows[0]


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
    assert "Email_Reviews" in workbook_xml
    assert "Email_Send_Logs" in workbook_xml
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


def test_result_package_v2_exports_email_review_and_send_logs(tmp_path: Path) -> None:
    result = make_pubmed_result(tmp_path)
    lead = result.leads[0]
    draft = make_draft(
        lead.lead_id,
        recipient_name=lead.pi_full_name,
        verified_email=lead.verified_email or "missing",
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-27T10:00:00",
        ),
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
    )
    permission = evaluate_send_permission(
        reviewed,
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
    )
    review = build_email_audit_record(
        event_type="email_batch_review",
        lead_id=lead.lead_id,
        actor="Reviewer",
        status_before="review_pending",
        status_after="review_approved",
        permission=permission,
        metadata={"draft_id": "draft-1"},
    )
    send_result = send_reviewed_email(
        reviewed,
        actor="Reviewer",
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
        provider=FakeProvider(),
        draft_id="draft-1",
        send_id="send-1",
    )

    package = build_result_package_from_pubmed_result(
        result,
        output_dir=tmp_path / "result_packages",
        email_drafts=[reviewed],
        email_reviews=[
            {
                "Event_ID": review.event_id,
                "Event_Type": review.event_type,
                "Lead_ID": review.lead_id,
                "Actor": review.actor,
                "Occurred_At": review.occurred_at,
                "Status_Before": review.status_before,
                "Status_After": review.status_after,
                "Permission_Allowed": review.permission_allowed,
                "Permission_Blockers": json.dumps(review.permission_blockers),
                "Note": review.note or "",
                "Metadata": json.dumps(review.metadata),
            }
        ],
        email_send_logs=[
            {
                "Send_ID": send_result.send_id,
                "Draft_ID": send_result.draft_id,
                "Lead_ID": send_result.lead_id,
                "Recipient_Email": send_result.recipient_email,
                "Provider": send_result.provider,
                "Status": send_result.status,
                "Provider_Message_ID": send_result.provider_message_id,
                "Attempted_At": send_result.attempted_at,
                "Finished_At": send_result.finished_at,
                "Actor": send_result.actor,
                "Permission_Allowed": send_result.permission_allowed,
                "Permission_Blockers": json.dumps(send_result.permission_blockers),
                "Permission_Warnings": json.dumps(send_result.permission_warnings),
                "Error_Type": send_result.error_type or "",
                "Error_Message": send_result.error_message or "",
            }
        ],
    )

    review_rows = read_csv(package.paths.email_reviews_csv)
    send_rows = read_csv(package.paths.email_send_logs_csv)

    assert review_rows[0]["Event_Type"] == "email_batch_review"
    assert send_rows[0]["Status"] == "sent"
    assert package.row_counts["email_reviews"] == 1
    assert package.row_counts["email_send_logs"] == 1


def test_result_package_can_be_built_from_database_task(tmp_path: Path) -> None:
    result = make_pubmed_result(tmp_path)
    lead = result.leads[0]
    draft = make_draft(
        lead.lead_id,
        recipient_name=lead.pi_full_name,
        verified_email=lead.verified_email or "missing",
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(reviewer="Reviewer", decision="approve"),
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
    )
    send_result = send_reviewed_email(
        reviewed,
        actor="Reviewer",
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=5,
        ),
        provider=FakeProvider(),
        draft_id="draft-1",
        send_id="send-1",
    )

    with initialize_database(tmp_path / "package.sqlite") as connection:
        insert_task(
            connection,
            task_id=result.task_id,
            task_type="pubmed",
            status="success",
            query=result.search_params.query,
            parameters={
                "from_date": result.search_params.from_date,
                "to_date": result.search_params.to_date,
                "max_results": result.search_params.max_results,
            },
        )
        for paper in result.papers:
            insert_pubmed_paper(connection, paper, task_id=result.task_id)
        insert_pubmed_lead(connection, lead, task_id=result.task_id)
        insert_email_draft(connection, reviewed, draft_id="draft-1")
        insert_email_review_record(connection, email_send_result_to_dict(send_result)["audit_record"])
        insert_email_send_log(connection, email_send_result_to_dict(send_result))

        package = build_result_package_from_database_task(
            connection,
            task_id=result.task_id,
            output_dir=tmp_path / "db_packages",
            created_at="2026-08-27T11:00:00",
        )

    assert package.package_id == "TASK_pubmed_stage33"
    assert read_csv(package.paths.email_send_logs_csv)[0]["Send_ID"] == "send-1"
    assert package.row_counts["email_send_logs"] == 1
