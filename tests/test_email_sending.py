import json

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.database import (
    fetch_one,
    initialize_database,
    insert_email_draft,
    insert_email_send_log,
    insert_pubmed_lead,
)
from scholarlead_agent.email_review import EmailReviewDecision, PermissionPolicy, apply_email_review_decision
from scholarlead_agent.email_sending import (
    EmailProviderResult,
    build_email_send_request,
    email_send_result_to_dict,
    send_reviewed_email,
)
from scholarlead_agent.pubmed_models import PubMedLead


class FakeProvider:
    provider_name = "fake-provider"

    def __init__(self, *, result: EmailProviderResult | None = None, error: Exception | None = None) -> None:
        self.result = result or EmailProviderResult(
            success=True,
            provider=self.provider_name,
            provider_message_id="message-1",
        )
        self.error = error
        self.calls = []

    def send(self, request):
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return self.result


def make_draft(**overrides):
    draft = build_email_draft(
        evidence=EmailDraftInput(
            lead_id="pubmed-41951915-lei-s-qi",
            pi_full_name="Lei S Qi",
            recent_publication_title="CRISPR-Cas-based live cell imaging of genome dynamics",
            source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
            target_service_type="single-cell RNA sequencing",
            verified_email="slqi@stanford.edu",
            email_status="verified_from_pubmed_affiliation",
        ),
        subject="Collaboration around CRISPR imaging",
        body="Dear Dr. Qi,\n\nI read your recent paper.\n\nBest regards,",
        model_name="fake-email-model",
        generated_at="2026-08-24T10:00:00",
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-24T10:05:00",
        ),
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=10,
        ),
    )
    reviewed.update(overrides)
    return reviewed


def make_lead() -> PubMedLead:
    return PubMedLead(
        lead_id="pubmed-41951915-lei-s-qi",
        pi_full_name="Lei S Qi",
        verified_email="slqi@stanford.edu",
        email_status="verified_from_pubmed_affiliation",
        email_source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        email_source_type="pubmed_affiliation",
        name_email_match_confidence="high",
        institution="Stanford University",
        country="United States",
        country_confidence="high",
        recent_publication_title="CRISPR-Cas-based live cell imaging of genome dynamics",
        abstract="Abstract text.",
        journal="Example Journal",
        publication_year=2026,
        pmid="41951915",
        doi="10.1000/example",
        author_role="email_author",
        source_links=["https://pubmed.ncbi.nlm.nih.gov/41951915/"],
        data_quality="email_evidence_available",
        manual_review_required=False,
        notes="Test lead.",
    )


def allow_policy() -> PermissionPolicy:
    return PermissionPolicy(
        real_email_sending_enabled=True,
        sender_account_configured=True,
        daily_send_quota=10,
        sent_today=0,
    )


def test_send_reviewed_email_blocks_without_provider_and_does_not_send() -> None:
    result = send_reviewed_email(
        make_draft(),
        actor="Reviewer",
        policy=allow_policy(),
        provider=None,
        send_id="send-1",
    )

    assert result.status == "blocked"
    assert result.permission_allowed is False
    assert "send_provider_not_configured" in result.permission_blockers
    assert result.error_type == "PermissionBlocked"
    assert result.audit_record is not None
    assert result.audit_record.event_type == "email_send_blocked"


def test_send_reviewed_email_blocks_unapproved_draft_before_provider_call() -> None:
    provider = FakeProvider()
    result = send_reviewed_email(
        make_draft(draft_status="review_pending"),
        actor="Reviewer",
        policy=allow_policy(),
        provider=provider,
        send_id="send-1",
    )

    assert result.status == "blocked"
    assert "human_review_not_approved" in result.permission_blockers
    assert provider.calls == []


def test_send_reviewed_email_blocks_missing_verified_email_before_provider_call() -> None:
    provider = FakeProvider()
    result = send_reviewed_email(
        make_draft(verified_email=None, email_status="missing"),
        actor="Reviewer",
        policy=allow_policy(),
        provider=provider,
        send_id="send-1",
    )

    assert result.status == "blocked"
    assert "missing_verified_email" in result.permission_blockers
    assert provider.calls == []


def test_send_reviewed_email_sends_once_when_policy_and_provider_are_ready(tmp_path) -> None:
    provider = FakeProvider()
    audit_path = tmp_path / "email_audit.jsonl"

    result = send_reviewed_email(
        make_draft(),
        actor="Reviewer",
        policy=allow_policy(),
        provider=provider,
        send_id="send-1",
        draft_id="draft-1",
        audit_path=audit_path,
    )

    assert result.status == "sent"
    assert result.provider == "fake-provider"
    assert result.provider_message_id == "message-1"
    assert result.permission_allowed is True
    assert result.permission_blockers == []
    assert len(provider.calls) == 1
    assert provider.calls[0].recipient_email == "slqi@stanford.edu"
    assert provider.calls[0].subject == "Collaboration around CRISPR imaging"

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_type"] == "email_send_sent"


def test_send_reviewed_email_records_provider_failure() -> None:
    provider = FakeProvider(error=RuntimeError("provider down"))

    result = send_reviewed_email(
        make_draft(),
        actor="Reviewer",
        policy=allow_policy(),
        provider=provider,
        send_id="send-1",
    )

    assert result.status == "failed"
    assert result.permission_allowed is True
    assert result.error_type == "RuntimeError"
    assert result.error_message == "provider down"
    assert len(provider.calls) == 1
    assert result.audit_record is not None
    assert result.audit_record.event_type == "email_send_failed"


def test_provider_failure_result_is_failed_without_exception() -> None:
    provider = FakeProvider(
        result=EmailProviderResult(
            success=False,
            provider="fake-provider",
            error_type="Rejected",
            error_message="provider rejected message",
        )
    )

    result = send_reviewed_email(
        make_draft(),
        actor="Reviewer",
        policy=allow_policy(),
        provider=provider,
        send_id="send-1",
    )

    assert result.status == "failed"
    assert result.error_type == "Rejected"
    assert result.error_message == "provider rejected message"


def test_build_email_send_request_requires_core_fields() -> None:
    request = build_email_send_request(
        make_draft(),
        actor="Reviewer",
        provider_name="fake-provider",
        send_id="send-1",
        idempotency_key="idem-1",
    )

    assert request.send_id == "send-1"
    assert request.idempotency_key == "idem-1"
    assert request.recipient_email == "slqi@stanford.edu"
    assert request.actor == "Reviewer"


def test_email_send_result_can_be_saved_to_database(tmp_path) -> None:
    result = send_reviewed_email(
        make_draft(),
        actor="Reviewer",
        policy=allow_policy(),
        provider=FakeProvider(),
        send_id="send-1",
        draft_id="draft-1",
    )

    with initialize_database(tmp_path / "scholarlead.sqlite") as connection:
        insert_pubmed_lead(connection, make_lead())
        insert_email_draft(connection, make_draft(), draft_id="draft-1")
        insert_email_send_log(connection, email_send_result_to_dict(result))

        row = fetch_one(
            connection,
            "SELECT * FROM email_send_logs WHERE send_id = ?",
            ("send-1",),
        )

    assert row is not None
    assert row["status"] == "sent"
    assert row["provider_message_id"] == "message-1"
    assert json.loads(row["permission_blockers_json"]) == []
