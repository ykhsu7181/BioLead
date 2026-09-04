from pathlib import Path

from scholarlead_agent.database import (
    initialize_database,
    insert_email_draft,
    insert_email_send_log,
    insert_pubmed_lead,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.services.lead_contact_status import (
    fetch_lead_contact_statuses,
)


def make_lead(lead_id: str) -> PubMedLead:
    return PubMedLead(
        lead_id=lead_id,
        pi_full_name=f"PI {lead_id}",
        verified_email=f"{lead_id}@example.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Example University",
        country="United States",
        country_confidence="high",
        recent_publication_title="Single-cell study",
        abstract="Abstract.",
        journal="Journal",
        publication_year=2026,
        pmid="1",
        doi=None,
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/1/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Test.",
    )


def test_lead_contact_status_uses_multi_draft_priority_and_formal_send_semantics(
    tmp_path: Path,
) -> None:
    with initialize_database(tmp_path / "contacts.sqlite") as connection:
        for lead_id in ("none", "pending", "rejected", "ready", "sent"):
            insert_pubmed_lead(connection, make_lead(lead_id))
        insert_email_draft(
            connection,
            {"lead_id": "pending", "draft_status": "review_pending"},
            draft_id="draft-pending",
        )
        insert_email_draft(
            connection,
            {"lead_id": "rejected", "draft_status": "review_rejected"},
            draft_id="draft-rejected",
        )
        for lead_id in ("ready", "sent"):
            insert_email_draft(
                connection,
                {"lead_id": lead_id, "draft_status": "review_approved"},
                draft_id=f"draft-{lead_id}",
            )
        insert_email_send_log(
            connection,
            {
                "send_id": "test-send",
                "draft_id": "draft-ready",
                "lead_id": "ready",
                "status": "sent",
                "send_mode": "test_recipient",
            },
        )
        insert_email_send_log(
            connection,
            {
                "send_id": "formal-send",
                "draft_id": "draft-sent",
                "lead_id": "sent",
                "status": "sent",
                "send_mode": "real_recipient",
            },
        )

        statuses = fetch_lead_contact_statuses(connection)

    assert statuses == {
        "none": "not_contacted",
        "pending": "pending_review",
        "ready": "ready_to_send",
        "rejected": "rejected",
        "sent": "sent",
    }


def test_lead_contact_status_uses_highest_status_across_multiple_drafts(
    tmp_path: Path,
) -> None:
    with initialize_database(tmp_path / "contacts.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        for draft_id, draft_status in (
            ("rejected", "review_rejected"),
            ("pending", "review_pending"),
            ("approved", "review_approved"),
        ):
            insert_email_draft(
                connection,
                {"lead_id": "lead-1", "draft_status": draft_status},
                draft_id=draft_id,
            )

        statuses = fetch_lead_contact_statuses(connection, ["lead-1"])

    assert statuses == {"lead-1": "ready_to_send"}
