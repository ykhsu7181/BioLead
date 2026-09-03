import json
from pathlib import Path

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.config import AppConfig
from scholarlead_agent.database import (
    fetch_all,
    fetch_one,
    initialize_database,
    insert_email_draft,
    insert_pubmed_lead,
)
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    apply_email_review_decision,
)
from scholarlead_agent.email_sending import EmailProviderResult
from scholarlead_agent.email_smtp import build_email_send_policy_from_config
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.services.email_batch_service import (
    BATCH_SEND_MODE_PERMISSION_CHECK,
    BATCH_SEND_MODE_REAL_RECIPIENT,
    apply_batch_email_review,
    generate_batch_email_drafts,
    send_batch_reviewed_emails,
)


class FakeDraftService:
    def __init__(self) -> None:
        self.calls = []

    def generate_for_lead(self, lead):
        self.calls.append(lead.lead_id)
        return build_email_draft(
            evidence=EmailDraftInput(
                lead_id=lead.lead_id,
                pi_full_name=lead.pi_full_name,
                recent_publication_title=lead.recent_publication_title,
                source_url=lead.source_links[0],
                target_service_type=lead.target_service_type or "single-cell RNA sequencing",
                verified_email=lead.verified_email,
                email_status=lead.email_status,
            ),
            subject=f"Question about {lead.pi_full_name}'s study",
            body=f"Dear Dr. {lead.pi_full_name.split()[-1]},\n\nI read your paper.\n\nBest regards,",
            model_name="fake-batch-model",
            generated_at="2026-08-27T10:00:00",
        )


class FakeProvider:
    provider_name = "fake-provider"

    def __init__(self) -> None:
        self.calls = []

    def send(self, request):
        self.calls.append(request)
        return EmailProviderResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=f"message-{len(self.calls)}",
        )


def make_config(**overrides):
    values = {
        "email_provider": "smtp",
        "email_send_enabled": True,
        "email_sender": "agent_test@yeah.net",
        "email_test_recipient": "tester@qq.com",
        "email_allowed_recipients": ("tester@qq.com",),
        "email_daily_limit": 5,
        "smtp_host": "smtp.yeah.net",
        "smtp_port": 465,
        "smtp_username": "agent_test@yeah.net",
        "smtp_password": "authorization-code",
        "smtp_use_ssl": True,
        "smtp_timeout_seconds": 30,
    }
    values.update(overrides)
    return AppConfig(**values)


def make_lead(lead_id: str = "lead-1", email: str = "alice@example.edu") -> PubMedLead:
    return PubMedLead(
        lead_id=lead_id,
        pi_full_name="Alice Smith",
        verified_email=email,
        email_status="verified_from_pubmed_affiliation" if email else "missing",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Example University",
        country="United States",
        country_confidence="high",
        recent_publication_title="Single-cell RNA sequencing in cancer",
        abstract="A single-cell cancer study.",
        journal="Example Journal",
        publication_year=2026,
        pmid="1",
        doi="10.1000/example",
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/1/"],
        data_quality="email_evidence_available" if email else "missing_email_candidate",
        manual_review_required=not bool(email),
        notes="Test lead.",
        matched_keywords=["single-cell", "cancer"],
        target_service_type="single-cell RNA sequencing",
    )


def make_reviewed_draft(lead_id: str = "lead-1"):
    draft = build_email_draft(
        evidence=EmailDraftInput(
            lead_id=lead_id,
            pi_full_name="Alice Smith",
            recent_publication_title="Single-cell RNA sequencing in cancer",
            source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            target_service_type="single-cell RNA sequencing",
            verified_email="alice@example.edu",
            email_status="verified_from_pubmed_affiliation",
        ),
        subject="Question about your single-cell cancer study",
        body="Dear Dr. Smith,\n\nI read your paper.\n\nBest regards,",
        model_name="fake-model",
        generated_at="2026-08-27T10:00:00",
    )
    return apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-27T10:05:00",
        ),
        policy=build_email_send_policy_from_config(make_config()),
    )


def test_batch_generate_email_drafts_persists_drafts_and_job(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "batch.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        insert_pubmed_lead(connection, make_lead("lead-2"))
        service = FakeDraftService()

        result = generate_batch_email_drafts(
            connection,
            lead_ids=["lead-1", "lead-2"],
            service=service,
            job_id="job-drafts",
        )

        drafts = fetch_all(connection, "SELECT * FROM email_drafts ORDER BY draft_id")
        job = fetch_one(connection, "SELECT * FROM jobs WHERE job_id = ?", ("job-drafts",))

    assert result.status == "completed"
    assert result.success_count == 2
    assert result.draft_ids == ["draft-lead-1", "draft-lead-2"]
    assert service.calls == ["lead-1", "lead-2"]
    assert [row["draft_id"] for row in drafts] == ["draft-lead-1", "draft-lead-2"]
    assert job["job_type"] == "BatchDraftJob"


def test_batch_regeneration_creates_a_new_version_without_overwriting_history(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "batch.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        service = FakeDraftService()
        first = generate_batch_email_drafts(
            connection,
            lead_ids=["lead-1"],
            service=service,
            job_id="job-drafts-1",
        )
        second = generate_batch_email_drafts(
            connection,
            lead_ids=["lead-1"],
            service=service,
            job_id="job-drafts-2",
        )
        drafts = fetch_all(connection, "SELECT * FROM email_drafts ORDER BY draft_id")

    assert first.draft_ids == ["draft-lead-1"]
    assert second.draft_ids == ["draft-lead-1-v2"]
    assert [row["draft_id"] for row in drafts] == ["draft-lead-1", "draft-lead-1-v2"]


def test_batch_review_updates_drafts_and_records_audit(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "batch.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        insert_email_draft(connection, make_reviewed_draft("lead-1"), draft_id="draft-lead-1")

        result = apply_batch_email_review(
            connection,
            draft_ids=["draft-lead-1", "missing"],
            reviewer="Reviewer",
            decision="reject",
            comments="Not relevant.",
        )

        draft = fetch_one(connection, "SELECT * FROM email_drafts WHERE draft_id = ?", ("draft-lead-1",))
        reviews = fetch_all(connection, "SELECT * FROM email_reviews")

    assert result.reviewed_count == 1
    assert result.missing_draft_ids == ["missing"]
    assert draft["draft_status"] == "review_rejected"
    assert len(reviews) == 1
    assert reviews[0]["event_type"] == "email_batch_review"


def test_batch_send_permission_check_does_not_call_provider_and_logs_blocked(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "batch.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        insert_email_draft(connection, make_reviewed_draft("lead-1"), draft_id="draft-lead-1")
        provider = FakeProvider()

        result = send_batch_reviewed_emails(
            connection,
            draft_ids=["draft-lead-1"],
            actor="Reviewer",
            mode=BATCH_SEND_MODE_PERMISSION_CHECK,
            config=make_config(),
            provider=provider,
            job_id="job-send-check",
        )

        logs = fetch_all(connection, "SELECT * FROM email_send_logs")
        payload = json.loads(logs[0]["payload_json"])

    assert result.status == "blocked"
    assert result.blocked_count == 1
    assert provider.calls == []
    assert logs[0]["status"] == "blocked"
    assert payload["send_mode"] == "permission_check"
    assert "permission_check_only" in payload["permission_blockers"]


def test_batch_send_real_recipient_uses_injected_provider_and_persists_log(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "batch.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead("lead-1"))
        insert_email_draft(connection, make_reviewed_draft("lead-1"), draft_id="draft-lead-1")
        provider = FakeProvider()

        result = send_batch_reviewed_emails(
            connection,
            draft_ids=["draft-lead-1"],
            actor="Reviewer",
            mode=BATCH_SEND_MODE_REAL_RECIPIENT,
            config=make_config(),
            provider=provider,
            job_id="job-send-real",
        )

        logs = fetch_all(connection, "SELECT * FROM email_send_logs")
        payload = json.loads(logs[0]["payload_json"])

    assert result.status == "completed"
    assert result.sent_count == 1
    assert len(provider.calls) == 1
    assert provider.calls[0].recipient_email == "alice@example.edu"
    assert logs[0]["status"] == "sent"
    assert logs[0]["provider_message_id"] == "message-1"
    assert payload["send_mode"] == "real_recipient"
