from scholarlead_agent.ai.email_drafts import EmailDraftInput, build_email_draft
from scholarlead_agent.config import AppConfig
from scholarlead_agent.email_review import EmailReviewDecision, apply_email_review_decision
from scholarlead_agent.email_smtp import (
    SmtpEmailProvider,
    SmtpEmailProviderConfig,
    build_email_send_policy_from_config,
    build_test_send_draft,
    build_test_send_preview,
    send_reviewed_test_email,
)


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.logged_in = None
        self.messages = []
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.messages.append(message)


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


def make_reviewed_draft(**overrides):
    draft = build_email_draft(
        evidence=EmailDraftInput(
            lead_id="lead-1",
            pi_full_name="Alice Smith",
            recent_publication_title="Spatial transcriptomics in cancer",
            source_url="https://pubmed.ncbi.nlm.nih.gov/1/",
            target_service_type="spatial transcriptomics",
            verified_email="alice@example.edu",
            email_status="verified_from_pubmed_affiliation",
        ),
        subject="Collaboration around spatial transcriptomics",
        body="Dear Dr. Smith,\n\nI read your recent work.\n\nBest regards,",
        model_name="fake-model",
        generated_at="2026-08-25T10:00:00",
    )
    reviewed = apply_email_review_decision(
        draft,
        EmailReviewDecision(
            reviewer="Reviewer",
            decision="approve",
            reviewed_at="2026-08-25T10:05:00",
        ),
        policy=build_email_send_policy_from_config(make_config()),
    )
    reviewed.update(overrides)
    return reviewed


def test_build_test_send_draft_replaces_pi_email_with_test_recipient() -> None:
    draft, blockers = build_test_send_draft(make_reviewed_draft(), make_config())

    assert blockers == []
    assert draft["original_verified_email"] == "alice@example.edu"
    assert draft["verified_email"] == "tester@qq.com"
    assert draft["actual_send_recipient"] == "tester@qq.com"
    assert draft["send_mode"] == "test_recipient"


def test_build_test_send_draft_blocks_non_whitelisted_test_recipient() -> None:
    _, blockers = build_test_send_draft(
        make_reviewed_draft(),
        make_config(email_allowed_recipients=("other@qq.com",)),
    )

    assert "test_recipient_not_allowed" in blockers


def test_build_test_send_preview_combines_config_and_permission_blockers() -> None:
    preview = build_test_send_preview(
        make_reviewed_draft(),
        make_config(email_send_enabled=False),
    )

    assert preview["allowed"] is False
    assert "real_email_sending_disabled" in preview["blockers"]
    assert preview["actual_recipient"] == "tester@qq.com"


def test_smtp_provider_uses_smtp_ssl_without_real_network(monkeypatch) -> None:
    FakeSMTP.instances = []
    monkeypatch.setattr("smtplib.SMTP_SSL", FakeSMTP)
    provider = SmtpEmailProvider(
        SmtpEmailProviderConfig(
            host="smtp.yeah.net",
            port=465,
            username="agent_test@yeah.net",
            password="authorization-code",
            sender="agent_test@yeah.net",
        )
    )

    result = send_reviewed_test_email(
        make_reviewed_draft(),
        actor="Reviewer",
        config=make_config(),
        provider=provider,
        send_id="send-1",
    )

    assert result.status == "sent"
    assert result.recipient_email == "tester@qq.com"
    assert len(FakeSMTP.instances) == 1
    instance = FakeSMTP.instances[0]
    assert instance.host == "smtp.yeah.net"
    assert instance.logged_in == ("agent_test@yeah.net", "authorization-code")
    assert instance.messages[0]["To"] == "tester@qq.com"
    assert instance.messages[0]["X-ScholarLead-Send-ID"] == "send-1"


def test_send_reviewed_test_email_blocks_when_provider_disabled() -> None:
    result = send_reviewed_test_email(
        make_reviewed_draft(),
        actor="Reviewer",
        config=make_config(email_send_enabled=False),
        provider=None,
        send_id="send-1",
    )

    assert result.status == "blocked"
    assert "real_email_sending_disabled" in result.permission_blockers


def test_send_reviewed_test_email_blocks_non_whitelisted_recipient_before_provider() -> None:
    result = send_reviewed_test_email(
        make_reviewed_draft(),
        actor="Reviewer",
        config=make_config(email_allowed_recipients=("other@qq.com",)),
        provider=None,
        send_id="send-1",
    )

    assert result.status == "blocked"
    assert "test_recipient_not_allowed" in result.permission_blockers
