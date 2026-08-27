"""Controlled email sending boundary for Stage 25.

This module implements the minimum send loop around already-reviewed drafts.
It does not configure SMTP or any external provider by default. A caller must
explicitly inject a provider, and permission checks must pass before that
provider is invoked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from scholarlead_agent.ai.email_drafts import EmailDraft, email_draft_to_dict
from scholarlead_agent.email_review import (
    EmailAuditRecord,
    PermissionPolicy,
    SendPermissionResult,
    append_email_audit_record,
    build_email_audit_record,
    evaluate_send_permission,
)


SEND_STATUS_BLOCKED = "blocked"
SEND_STATUS_SENT = "sent"
SEND_STATUS_FAILED = "failed"
EMAIL_SEND_POLICY_VERSION = "email_send_policy_v1"


@dataclass(frozen=True)
class EmailSendRequest:
    """Provider-ready request for one reviewed email draft."""

    send_id: str
    lead_id: str
    draft_id: str | None
    recipient_email: str
    recipient_name: str | None
    subject: str
    body: str
    actor: str
    provider: str
    idempotency_key: str
    attempted_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmailProviderResult:
    """Result returned by an injected email provider."""

    success: bool
    provider: str
    provider_message_id: str | None = None
    status: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EmailSendResult:
    """Auditable result for one send attempt or send block."""

    send_id: str
    lead_id: str
    draft_id: str | None
    recipient_email: str | None
    status: str
    provider: str | None
    provider_message_id: str | None
    attempted_at: str
    finished_at: str
    actor: str
    permission_allowed: bool
    permission_blockers: list[str] = field(default_factory=list)
    permission_warnings: list[str] = field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
    audit_record: EmailAuditRecord | None = None


class EmailProvider(Protocol):
    """Protocol for a future SMTP or API email provider."""

    provider_name: str

    def send(self, request: EmailSendRequest) -> EmailProviderResult:
        """Send one reviewed email."""


def build_email_send_request(
    draft: EmailDraft | dict[str, Any],
    *,
    actor: str,
    provider_name: str,
    draft_id: str | None = None,
    send_id: str | None = None,
    attempted_at: str | None = None,
    idempotency_key: str | None = None,
) -> EmailSendRequest:
    """Build a provider request from a reviewed draft."""

    data = _draft_to_dict(draft)
    normalized_actor = _require_text(actor, "actor")
    recipient_email = _require_text(data.get("verified_email"), "verified_email")
    subject = _require_text(data.get("subject"), "subject")
    body = _require_text(data.get("body"), "body")
    lead_id = _require_text(data.get("lead_id"), "lead_id")
    request_send_id = send_id or str(uuid4())

    return EmailSendRequest(
        send_id=request_send_id,
        lead_id=lead_id,
        draft_id=draft_id or _clean_text(data.get("draft_id")),
        recipient_email=recipient_email,
        recipient_name=_clean_text(data.get("recipient_name")),
        subject=subject,
        body=body,
        actor=normalized_actor,
        provider=_require_text(provider_name, "provider_name"),
        idempotency_key=idempotency_key or request_send_id,
        attempted_at=attempted_at or _now(),
        metadata={
            "source_pmid": data.get("source_pmid"),
            "source_url": data.get("source_url"),
            "target_service_type": data.get("target_service_type"),
        },
    )


def send_reviewed_email(
    draft: EmailDraft | dict[str, Any],
    *,
    actor: str,
    policy: PermissionPolicy | None = None,
    provider: EmailProvider | None = None,
    draft_id: str | None = None,
    send_id: str | None = None,
    audit_path: Path | None = None,
    extra_blockers: list[str] | None = None,
) -> EmailSendResult:
    """Attempt one controlled send after review and permission checks.

    If permission fails or no provider is injected, the provider is not called.
    """

    data = _draft_to_dict(draft)
    normalized_actor = _require_text(actor, "actor")
    attempted_at = _now()
    result_send_id = send_id or str(uuid4())
    permission = evaluate_send_permission(data, policy=policy)

    blockers = list(permission.blockers)
    blockers.extend(extra_blockers or [])
    if provider is None:
        blockers.append("send_provider_not_configured")

    if blockers:
        blocked_permission = SendPermissionResult(
            allowed=False,
            status="blocked",
            blockers=blockers,
            warnings=permission.warnings,
            policy_version=permission.policy_version,
        )
        result = _build_result(
            send_id=result_send_id,
            draft=data,
            draft_id=draft_id,
            status=SEND_STATUS_BLOCKED,
            provider=getattr(provider, "provider_name", None),
            actor=normalized_actor,
            permission=blocked_permission,
            attempted_at=attempted_at,
            error_type="PermissionBlocked",
            error_message=", ".join(blockers),
        )
        _append_audit_if_requested(result, audit_path)
        return result

    assert provider is not None
    request = build_email_send_request(
        data,
        actor=normalized_actor,
        provider_name=provider.provider_name,
        draft_id=draft_id,
        send_id=result_send_id,
        attempted_at=attempted_at,
    )

    try:
        provider_result = provider.send(request)
    except Exception as error:
        result = _build_result(
            send_id=result_send_id,
            draft=data,
            draft_id=draft_id,
            status=SEND_STATUS_FAILED,
            provider=provider.provider_name,
            actor=normalized_actor,
            permission=permission,
            attempted_at=attempted_at,
            error_type=error.__class__.__name__,
            error_message=str(error),
        )
        _append_audit_if_requested(result, audit_path)
        return result

    status = SEND_STATUS_SENT if provider_result.success else SEND_STATUS_FAILED
    result = _build_result(
        send_id=result_send_id,
        draft=data,
        draft_id=draft_id,
        status=status,
        provider=provider_result.provider,
        provider_message_id=provider_result.provider_message_id,
        actor=normalized_actor,
        permission=permission,
        attempted_at=attempted_at,
        error_type=provider_result.error_type,
        error_message=provider_result.error_message,
    )
    _append_audit_if_requested(result, audit_path)
    return result


def email_send_result_to_dict(result: EmailSendResult) -> dict[str, Any]:
    """Convert one send result to a database- and JSON-ready dictionary."""

    return {
        "send_id": result.send_id,
        "lead_id": result.lead_id,
        "draft_id": result.draft_id,
        "recipient_email": result.recipient_email,
        "status": result.status,
        "provider": result.provider,
        "provider_message_id": result.provider_message_id,
        "attempted_at": result.attempted_at,
        "finished_at": result.finished_at,
        "actor": result.actor,
        "permission_allowed": result.permission_allowed,
        "permission_blockers": result.permission_blockers,
        "permission_warnings": result.permission_warnings,
        "error_type": result.error_type,
        "error_message": result.error_message,
        "audit_record": _audit_to_dict(result.audit_record),
    }


def _build_result(
    *,
    send_id: str,
    draft: dict[str, Any],
    draft_id: str | None,
    status: str,
    provider: str | None,
    actor: str,
    permission: SendPermissionResult,
    attempted_at: str,
    provider_message_id: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> EmailSendResult:
    finished_at = _now()
    lead_id = str(draft.get("lead_id") or "")
    audit_record = build_email_audit_record(
        event_type=f"email_send_{status}",
        lead_id=lead_id,
        actor=actor,
        status_before=str(draft.get("draft_status") or ""),
        status_after=status,
        permission=permission,
        note=error_message,
        metadata={
            "send_id": send_id,
            "draft_id": draft_id,
            "provider": provider,
            "provider_message_id": provider_message_id,
        },
        occurred_at=finished_at,
    )
    return EmailSendResult(
        send_id=send_id,
        lead_id=lead_id,
        draft_id=draft_id,
        recipient_email=_clean_text(draft.get("verified_email")),
        status=status,
        provider=provider,
        provider_message_id=provider_message_id,
        attempted_at=attempted_at,
        finished_at=finished_at,
        actor=actor,
        permission_allowed=permission.allowed,
        permission_blockers=permission.blockers,
        permission_warnings=permission.warnings,
        error_type=error_type,
        error_message=error_message,
        audit_record=audit_record,
    )


def _append_audit_if_requested(result: EmailSendResult, audit_path: Path | None) -> None:
    if audit_path is not None and result.audit_record is not None:
        append_email_audit_record(result.audit_record, audit_path)


def _audit_to_dict(record: EmailAuditRecord | None) -> dict[str, Any] | None:
    if record is None:
        return None
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


def _draft_to_dict(draft: EmailDraft | dict[str, Any]) -> dict[str, Any]:
    if isinstance(draft, EmailDraft):
        return email_draft_to_dict(draft)
    if isinstance(draft, dict):
        return dict(draft)
    raise ValueError("draft must be an EmailDraft or dictionary")


def _require_text(value: Any, field_name: str) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
