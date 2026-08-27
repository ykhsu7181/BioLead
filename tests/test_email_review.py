import json

import pytest

from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.agent.runtime import build_default_tool_registry
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    PermissionPolicy,
    append_email_audit_record,
    apply_email_review_decision,
    build_email_audit_record,
    email_audit_record_to_dict,
    evaluate_send_permission,
)


def make_draft(**overrides):
    evidence = EmailDraftInput(
        lead_id="pubmed-41951915-lei-s-qi",
        pi_full_name="Lei S Qi",
        recent_publication_title=(
            "CRISPR-Cas-based live cell imaging of genome dynamics"
        ),
        source_url="https://pubmed.ncbi.nlm.nih.gov/41951915/",
        target_service_type="single-cell RNA sequencing",
        verified_email="slqi@stanford.edu",
        email_status="verified_from_pubmed_affiliation",
        pmid="41951915",
        institution="Stanford University",
        country="United States",
    )
    draft = build_email_draft(
        evidence=evidence,
        subject="Collaboration around CRISPR imaging",
        body="Dear Dr. Qi,\n\nI read your recent publication.\n\nBest regards,",
        model_name="fake-email-model",
        generated_at="2026-08-24T10:00:00",
    )
    data = {
        **draft.__dict__,
        "evidence": draft.evidence,
        "warnings": draft.warnings,
    }
    data.update(overrides)
    return data


def test_apply_email_review_approval_keeps_default_send_blocked() -> None:
    reviewed = apply_email_review_decision(
        make_draft(),
        EmailReviewDecision(
            reviewer="Senior Reviewer",
            decision="approve",
            comments="Looks acceptable after manual review.",
            reviewed_at="2026-08-24T10:05:00",
            edited_subject="Potential collaboration on CRISPR imaging",
        ),
    )

    assert reviewed["draft_status"] == "review_approved"
    assert reviewed["human_reviewer"] == "Senior Reviewer"
    assert reviewed["reviewed_at"] == "2026-08-24T10:05:00"
    assert reviewed["subject"] == "Potential collaboration on CRISPR imaging"
    assert reviewed["can_send"] is False
    assert reviewed["send_permission_status"] == "blocked"
    assert "real_email_sending_disabled" in reviewed["send_permission_blockers"]


def test_apply_email_review_supports_reject_and_changes_requested() -> None:
    rejected = apply_email_review_decision(
        make_draft(),
        EmailReviewDecision(reviewer="Reviewer", decision="reject"),
    )
    changes = apply_email_review_decision(
        make_draft(),
        EmailReviewDecision(reviewer="Reviewer", decision="request_changes"),
    )

    assert rejected["draft_status"] == "review_rejected"
    assert changes["draft_status"] == "changes_requested"
    assert "draft_rejected" in rejected["send_permission_warnings"]
    assert "draft_needs_revision" in changes["send_permission_warnings"]


def test_review_decision_requires_reviewer_and_valid_decision() -> None:
    with pytest.raises(ValueError, match="reviewer cannot be empty"):
        apply_email_review_decision(
            make_draft(),
            EmailReviewDecision(reviewer="", decision="approve"),
        )

    with pytest.raises(ValueError, match="decision must be"):
        apply_email_review_decision(
            make_draft(),
            EmailReviewDecision(reviewer="Reviewer", decision="send_now"),
        )


def test_permission_policy_allows_only_when_all_hard_conditions_pass() -> None:
    reviewed = apply_email_review_decision(
        make_draft(),
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-24T10:05:00",
        ),
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=10,
            sent_today=0,
        ),
    )

    assert reviewed["can_send"] is True
    assert reviewed["send_permission_status"] == "allowed"
    assert reviewed["send_permission_blockers"] == []


def test_permission_policy_blocks_missing_verified_email() -> None:
    draft = make_draft(verified_email=None, email_status="missing")
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

    assert reviewed["can_send"] is False
    assert "missing_verified_email" in reviewed["send_permission_blockers"]


def test_permission_policy_blocks_quota_exceeded() -> None:
    draft = make_draft(
        draft_status="review_approved",
        human_reviewer="Reviewer",
        reviewed_at="2026-08-24T10:05:00",
    )
    permission = evaluate_send_permission(
        draft,
        policy=PermissionPolicy(
            real_email_sending_enabled=True,
            sender_account_configured=True,
            daily_send_quota=2,
            sent_today=2,
        ),
    )

    assert permission.allowed is False
    assert "daily_send_quota_exceeded" in permission.blockers


def test_email_audit_record_omits_message_body_and_appends_jsonl(tmp_path) -> None:
    permission = evaluate_send_permission(make_draft())
    record = build_email_audit_record(
        event_type="review_decision",
        lead_id="pubmed-41951915-lei-s-qi",
        actor="Reviewer",
        status_before="review_pending",
        status_after="review_approved",
        permission=permission,
        note="Approved in UI",
        metadata={
            "source": "streamlit",
            "subject": "Sensitive subject should not be stored here",
            "body": "Sensitive body should not be stored here",
        },
        occurred_at="2026-08-24T10:10:00",
        event_id="event-1",
    )
    path = tmp_path / "email_audit.jsonl"

    append_email_audit_record(record, path)

    data = email_audit_record_to_dict(record)
    assert data["event_id"] == "event-1"
    assert data["permission_allowed"] is False
    assert "real_email_sending_disabled" in data["permission_blockers"]
    assert data["metadata"] == {"source": "streamlit"}

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event_id"] == "event-1"


def test_default_agent_registry_does_not_expose_send_email_tool() -> None:
    registry = build_default_tool_registry()

    assert "generate_email_draft" in registry.snapshot()
    assert "send_email" not in registry.snapshot()
