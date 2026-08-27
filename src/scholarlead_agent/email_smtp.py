"""SMTP email provider for controlled Stage 28 test sending.

The provider sends one already-reviewed draft through an SMTP account. It never
loads secrets into logs and is only used when trusted application code injects
it into the existing email_sending boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import smtplib
from typing import Any

from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.email_review import PermissionPolicy, evaluate_send_permission
from scholarlead_agent.email_sending import (
    EmailProviderResult,
    EmailSendResult,
    send_reviewed_email,
)


SMTP_PROVIDER_NAME = "smtp"


@dataclass(frozen=True)
class SmtpEmailProviderConfig:
    """Configuration required to send through SMTP."""

    host: str
    port: int
    username: str
    password: str
    sender: str
    use_ssl: bool = True
    timeout_seconds: int = 30

    @property
    def configured(self) -> bool:
        """Return whether the provider has enough non-secret settings to run."""

        return all(
            [
                _clean_text(self.host),
                self.port > 0,
                _clean_text(self.username),
                _clean_text(self.password),
                _clean_text(self.sender),
            ]
        )


class SmtpEmailProvider:
    """Send one reviewed email through an SMTP server."""

    provider_name = SMTP_PROVIDER_NAME

    def __init__(self, config: SmtpEmailProviderConfig) -> None:
        if not config.configured:
            raise ValueError("smtp provider is not configured")
        self.config = config

    def send(self, request) -> EmailProviderResult:
        message_id = make_msgid(domain="scholarlead-agent.local")
        message = EmailMessage()
        message["From"] = formataddr(("ScholarLead Agent", self.config.sender))
        message["To"] = request.recipient_email
        message["Subject"] = request.subject
        message["Message-ID"] = message_id
        message["X-ScholarLead-Send-ID"] = request.send_id
        message.set_content(request.body)

        try:
            if self.config.use_ssl:
                with smtplib.SMTP_SSL(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout_seconds,
                ) as server:
                    server.login(self.config.username, self.config.password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(
                    self.config.host,
                    self.config.port,
                    timeout=self.config.timeout_seconds,
                ) as server:
                    server.starttls()
                    server.login(self.config.username, self.config.password)
                    server.send_message(message)
        except Exception as error:
            return EmailProviderResult(
                success=False,
                provider=self.provider_name,
                error_type=error.__class__.__name__,
                error_message=str(error),
            )

        return EmailProviderResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=message_id,
            status="sent",
        )


def build_smtp_provider_config(config: AppConfig | None = None) -> SmtpEmailProviderConfig:
    """Build SMTP provider config from app config."""

    active_config = config or load_config()
    return SmtpEmailProviderConfig(
        host=active_config.smtp_host or "",
        port=active_config.smtp_port,
        username=active_config.smtp_username or "",
        password=active_config.smtp_password or "",
        sender=active_config.email_sender or active_config.smtp_username or "",
        use_ssl=active_config.smtp_use_ssl,
        timeout_seconds=active_config.smtp_timeout_seconds,
    )


def build_email_send_policy_from_config(
    config: AppConfig | None = None,
    *,
    sent_today: int = 0,
) -> PermissionPolicy:
    """Create the send permission policy implied by runtime config."""

    active_config = config or load_config()
    smtp_config = build_smtp_provider_config(active_config)
    return PermissionPolicy(
        real_email_sending_enabled=active_config.email_send_enabled,
        sender_account_configured=smtp_config.configured,
        daily_send_quota=active_config.email_daily_limit,
        sent_today=sent_today,
    )


def build_test_send_draft(
    draft: dict[str, Any],
    config: AppConfig | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Return a copy of draft that sends to the configured test recipient."""

    active_config = config or load_config()
    blockers: list[str] = []
    test_recipient = _clean_text(active_config.email_test_recipient)
    original_recipient = _clean_text(draft.get("verified_email"))

    if not original_recipient:
        blockers.append("missing_original_verified_email")
    if not test_recipient:
        blockers.append("test_recipient_not_configured")
    elif not _recipient_allowed(test_recipient, active_config.email_allowed_recipients):
        blockers.append("test_recipient_not_allowed")

    if active_config.email_provider.strip().lower() != SMTP_PROVIDER_NAME:
        blockers.append("email_provider_not_smtp")

    test_draft = dict(draft)
    if test_recipient:
        test_draft["verified_email"] = test_recipient
    test_draft["original_verified_email"] = original_recipient
    test_draft["actual_send_recipient"] = test_recipient
    test_draft["send_mode"] = "test_recipient"
    return test_draft, blockers


def send_reviewed_test_email(
    draft: dict[str, Any],
    *,
    actor: str,
    config: AppConfig | None = None,
    provider: SmtpEmailProvider | None = None,
    draft_id: str | None = None,
    send_id: str | None = None,
    audit_path=None,
    sent_today: int = 0,
) -> EmailSendResult:
    """Send one reviewed draft to EMAIL_TEST_RECIPIENT through SMTP."""

    active_config = config or load_config()
    test_draft, blockers = build_test_send_draft(draft, active_config)
    policy = build_email_send_policy_from_config(active_config, sent_today=sent_today)

    active_provider = provider
    if active_provider is None and not blockers:
        smtp_config = build_smtp_provider_config(active_config)
        if smtp_config.configured:
            active_provider = SmtpEmailProvider(smtp_config)

    return send_reviewed_email(
        test_draft,
        actor=actor,
        policy=policy,
        provider=active_provider,
        draft_id=draft_id,
        send_id=send_id,
        audit_path=audit_path,
        extra_blockers=blockers,
    )


def build_test_send_preview(
    draft: dict[str, Any],
    config: AppConfig | None = None,
) -> dict[str, Any]:
    """Build a UI-safe preview of the test-send target and safety state."""

    active_config = config or load_config()
    _, blockers = build_test_send_draft(draft, active_config)
    policy = build_email_send_policy_from_config(active_config)
    permission = evaluate_send_permission(draft, policy=policy)
    all_blockers = list(dict.fromkeys([*blockers, *permission.blockers]))
    return {
        "provider": active_config.email_provider,
        "send_enabled": active_config.email_send_enabled,
        "original_recipient": _clean_text(draft.get("verified_email")) or "missing",
        "actual_recipient": _clean_text(active_config.email_test_recipient) or "missing",
        "sender": _clean_text(active_config.email_sender) or "missing",
        "daily_limit": active_config.email_daily_limit,
        "allowed": not all_blockers,
        "blockers": all_blockers,
        "mode": "test_recipient",
    }


def _recipient_allowed(recipient: str, allowed_recipients: tuple[str, ...]) -> bool:
    normalized = recipient.strip().lower()
    return normalized in {item.strip().lower() for item in allowed_recipients}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None
