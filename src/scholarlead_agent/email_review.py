"""Email draft review, permission checks, and audit records.

Stage 23 designs the human-review boundary before any real email sending exists.
The functions in this module are deterministic and do not send email.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from scholarlead_agent.ai.email_drafts import EmailDraft, email_draft_to_dict


REVIEW_STATUS_PENDING = "review_pending"
REVIEW_STATUS_APPROVED = "review_approved"
REVIEW_STATUS_REJECTED = "review_rejected"
REVIEW_STATUS_CHANGES_REQUESTED = "changes_requested"

REVIEW_DECISION_APPROVE = "approve"
REVIEW_DECISION_REJECT = "reject"
REVIEW_DECISION_REQUEST_CHANGES = "request_changes"

EMAIL_REVIEW_POLICY_VERSION = "email_review_policy_v1"


@dataclass(frozen=True)
class EmailReviewDecision:
    """One human review decision for an email draft."""

    reviewer: str
    decision: str
    comments: str | None = None
    reviewed_at: str | None = None
    edited_subject: str | None = None
    edited_body: str | None = None


@dataclass(frozen=True)
class PermissionPolicy:
    """Configurable policy that must pass before future email sending."""

    real_email_sending_enabled: bool = False
    sender_account_configured: bool = False
    require_human_approval: bool = True
    require_verified_email: bool = True
    allowed_email_statuses: tuple[str, ...] = ("verified_from_pubmed_affiliation",)
    daily_send_quota: int = 0
    sent_today: int = 0
    policy_version: str = EMAIL_REVIEW_POLICY_VERSION


@dataclass(frozen=True)
class SendPermissionResult:
    """Result of checking whether a reviewed draft may be sent in the future."""

    allowed: bool
    status: str
    blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    policy_version: str = EMAIL_REVIEW_POLICY_VERSION


@dataclass(frozen=True)
class EmailAuditRecord:
    """Append-only audit event for review and permission decisions."""

    event_id: str
    event_type: str
    lead_id: str
    actor: str
    occurred_at: str
    status_before: str | None = None
    status_after: str | None = None
    permission_allowed: bool | None = None
    permission_blockers: list[str] = field(default_factory=list)
    note: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def apply_email_review_decision(
    draft: EmailDraft | dict[str, Any],
    decision: EmailReviewDecision,
    *,
    policy: PermissionPolicy | None = None,
) -> dict[str, Any]:
    """Apply one human review decision to a draft dictionary.

    The returned draft includes review metadata and permission results. It does
    not send email, and default policy keeps `can_send` false.
    """

    draft_data = _draft_to_dict(draft)
    normalized_decision = validate_email_review_decision(decision)
    status_after = _status_from_decision(normalized_decision.decision)

    if normalized_decision.edited_subject is not None:
        draft_data["subject"] = normalized_decision.edited_subject.strip()
    if normalized_decision.edited_body is not None:
        draft_data["body"] = normalized_decision.edited_body.strip()

    draft_data["draft_status"] = status_after
    draft_data["human_reviewer"] = normalized_decision.reviewer
    draft_data["reviewed_at"] = normalized_decision.reviewed_at or _now()
    draft_data["review_comments"] = normalized_decision.comments

    permission = evaluate_send_permission(draft_data, policy=policy)
    draft_data["can_send"] = permission.allowed
    draft_data["send_permission_status"] = permission.status
    draft_data["send_permission_blockers"] = permission.blockers
    draft_data["send_permission_warnings"] = permission.warnings
    draft_data["send_permission_policy_version"] = permission.policy_version
    return draft_data


def validate_email_review_decision(
    decision: EmailReviewDecision,
) -> EmailReviewDecision:
    """Validate and normalize a human review decision."""

    if not isinstance(decision, EmailReviewDecision):
        raise ValueError("decision must be an EmailReviewDecision")

    reviewer = _clean_text(decision.reviewer)
    if not reviewer:
        raise ValueError("reviewer cannot be empty")

    normalized_decision = _clean_text(decision.decision)
    if normalized_decision not in {
        REVIEW_DECISION_APPROVE,
        REVIEW_DECISION_REJECT,
        REVIEW_DECISION_REQUEST_CHANGES,
    }:
        raise ValueError("decision must be approve, reject, or request_changes")

    return EmailReviewDecision(
        reviewer=reviewer,
        decision=normalized_decision,
        comments=_clean_text(decision.comments),
        reviewed_at=_clean_text(decision.reviewed_at),
        edited_subject=_clean_text(decision.edited_subject),
        edited_body=_clean_text(decision.edited_body),
    )


def evaluate_send_permission(
    draft: EmailDraft | dict[str, Any],
    *,
    policy: PermissionPolicy | None = None,
) -> SendPermissionResult:
    """Evaluate whether a draft is allowed to be sent.

    This only evaluates permission. It does not invoke any sending provider.
    """

    draft_data = _draft_to_dict(draft)
    active_policy = policy or PermissionPolicy()
    blockers: list[str] = []
    warnings: list[str] = []

    if not active_policy.real_email_sending_enabled:
        blockers.append("real_email_sending_disabled")
    if active_policy.require_human_approval and draft_data.get("draft_status") != REVIEW_STATUS_APPROVED:
        blockers.append("human_review_not_approved")
    if active_policy.require_verified_email:
        verified_email = _clean_text(draft_data.get("verified_email"))
        email_status = _clean_text(draft_data.get("email_status"))
        if not verified_email:
            blockers.append("missing_verified_email")
        elif email_status not in active_policy.allowed_email_statuses:
            blockers.append("email_status_not_allowed")
    if active_policy.require_human_approval and not _clean_text(draft_data.get("human_reviewer")):
        blockers.append("missing_human_reviewer")
    if active_policy.require_human_approval and not _clean_text(draft_data.get("reviewed_at")):
        blockers.append("missing_review_timestamp")
    if not active_policy.sender_account_configured:
        blockers.append("sender_account_not_configured")
    if active_policy.daily_send_quota <= 0:
        blockers.append("daily_send_quota_not_configured")
    elif active_policy.sent_today >= active_policy.daily_send_quota:
        blockers.append("daily_send_quota_exceeded")
    if not _clean_text(draft_data.get("subject")):
        blockers.append("missing_subject")
    if not _clean_text(draft_data.get("body")):
        blockers.append("missing_body")

    quality_report = _quality_report_from_draft(draft_data)
    if quality_report.get("status") == "fail":
        blockers.append("draft_quality_failed")

    if draft_data.get("draft_status") == REVIEW_STATUS_CHANGES_REQUESTED:
        warnings.append("draft_needs_revision")
    if draft_data.get("draft_status") == REVIEW_STATUS_REJECTED:
        warnings.append("draft_rejected")

    return SendPermissionResult(
        allowed=not blockers,
        status="allowed" if not blockers else "blocked",
        blockers=blockers,
        warnings=warnings,
        policy_version=active_policy.policy_version,
    )


def build_email_audit_record(
    *,
    event_type: str,
    lead_id: str,
    actor: str,
    status_before: str | None = None,
    status_after: str | None = None,
    permission: SendPermissionResult | None = None,
    note: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: str | None = None,
    event_id: str | None = None,
) -> EmailAuditRecord:
    """Build one audit record without including secrets or message body text."""

    if not _clean_text(event_type):
        raise ValueError("event_type cannot be empty")
    if not _clean_text(lead_id):
        raise ValueError("lead_id cannot be empty")
    if not _clean_text(actor):
        raise ValueError("actor cannot be empty")

    return EmailAuditRecord(
        event_id=event_id or str(uuid4()),
        event_type=_clean_text(event_type) or "",
        lead_id=_clean_text(lead_id) or "",
        actor=_clean_text(actor) or "",
        occurred_at=occurred_at or _now(),
        status_before=_clean_text(status_before),
        status_after=_clean_text(status_after),
        permission_allowed=permission.allowed if permission is not None else None,
        permission_blockers=list(permission.blockers) if permission is not None else [],
        note=_clean_text(note),
        metadata=_safe_metadata(metadata or {}),
    )


def email_audit_record_to_dict(record: EmailAuditRecord) -> dict[str, Any]:
    """Convert an audit record to a plain dictionary."""

    return {
        "event_id": record.event_id,
        "event_type": record.event_type,
        "lead_id": record.lead_id,
        "actor": record.actor,
        "occurred_at": record.occurred_at,
        "status_before": record.status_before,
        "status_after": record.status_after,
        "permission_allowed": record.permission_allowed,
        "permission_blockers": record.permission_blockers,
        "note": record.note,
        "metadata": record.metadata,
    }


def append_email_audit_record(record: EmailAuditRecord, path: Path) -> None:
    """Append one audit record to JSONL storage."""

    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(email_audit_record_to_dict(record), ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(line + "\n")


def _status_from_decision(decision: str) -> str:
    if decision == REVIEW_DECISION_APPROVE:
        return REVIEW_STATUS_APPROVED
    if decision == REVIEW_DECISION_REJECT:
        return REVIEW_STATUS_REJECTED
    return REVIEW_STATUS_CHANGES_REQUESTED


def _draft_to_dict(draft: EmailDraft | dict[str, Any]) -> dict[str, Any]:
    if isinstance(draft, EmailDraft):
        return email_draft_to_dict(draft)
    if isinstance(draft, dict):
        return dict(draft)
    raise ValueError("draft must be an EmailDraft or dictionary")


def _quality_report_from_draft(draft_data: dict[str, Any]) -> dict[str, Any]:
    direct = draft_data.get("quality_report")
    if isinstance(direct, dict):
        return direct
    evidence = draft_data.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("quality_report"), dict):
        return evidence["quality_report"]
    return {}


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    blocked_keys = {"body", "subject", "api_key", "password", "token", "secret"}
    return {
        str(key): value
        for key, value in metadata.items()
        if str(key).lower() not in blocked_keys
    }


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
