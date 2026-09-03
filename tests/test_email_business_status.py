import json
from pathlib import Path

from scholarlead_agent.database import (
    initialize_database,
    insert_email_draft,
    insert_email_send_log,
)
from scholarlead_agent.services.email_business_status import (
    EMAIL_STATUS_PENDING_REVIEW,
    EMAIL_STATUS_READY_TO_SEND,
    EMAIL_STATUS_REJECTED,
    EMAIL_STATUS_SENT,
    SEND_MODE_UNKNOWN,
    describe_send_record,
    resolve_email_business_status,
    summarize_email_business_statuses,
)


def test_resolve_email_business_status_uses_shared_review_rules() -> None:
    assert resolve_email_business_status("review_pending") == EMAIL_STATUS_PENDING_REVIEW
    assert resolve_email_business_status("changes_requested") == EMAIL_STATUS_PENDING_REVIEW
    assert resolve_email_business_status("review_approved") == EMAIL_STATUS_READY_TO_SEND
    assert resolve_email_business_status("review_rejected") == EMAIL_STATUS_REJECTED


def test_only_formal_sent_record_takes_draft_out_of_ready_to_send() -> None:
    blocked = [{"status": "blocked", "payload_json": "{}"}]
    real_failed = [
        {
            "status": "failed",
            "payload_json": json.dumps({"send_mode": "real_recipient"}),
        }
    ]
    test_sent = [
        {
            "status": "sent",
            "payload_json": json.dumps({"send_mode": "test_recipient"}),
        }
    ]
    unknown_sent = [{"status": "sent", "payload_json": "{}"}]
    formal_sent = [
        {
            "status": "sent",
            "payload_json": json.dumps({"send_mode": "real_recipient"}),
        }
    ]

    assert resolve_email_business_status("review_approved", blocked) == EMAIL_STATUS_READY_TO_SEND
    assert resolve_email_business_status("review_approved", real_failed) == EMAIL_STATUS_READY_TO_SEND
    assert resolve_email_business_status("review_approved", test_sent) == EMAIL_STATUS_READY_TO_SEND
    assert resolve_email_business_status("review_approved", unknown_sent) == EMAIL_STATUS_READY_TO_SEND
    assert resolve_email_business_status("review_approved", formal_sent) == EMAIL_STATUS_SENT


def test_send_record_description_distinguishes_test_formal_and_legacy() -> None:
    test_send = describe_send_record(
        {"status": "sent", "payload": {"send_mode": "test_recipient"}}
    )
    formal_send = describe_send_record(
        {"status": "sent", "payload_json": '{"send_mode":"real_recipient"}'}
    )
    legacy_send = describe_send_record({"status": "sent", "payload_json": "{}"})

    assert test_send["send_label"] == "测试发送成功"
    assert test_send["is_formal_send_success"] is False
    assert formal_send["send_label"] == "正式发送成功"
    assert formal_send["is_formal_send_success"] is True
    assert legacy_send["send_mode"] == SEND_MODE_UNKNOWN
    assert legacy_send["is_formal_send_success"] is False


def test_business_status_summary_counts_drafts_and_only_formal_sends(tmp_path: Path) -> None:
    with initialize_database(tmp_path / "email-status.sqlite") as connection:
        for draft_id, draft_status in [
            ("pending", "review_pending"),
            ("changes", "changes_requested"),
            ("ready", "review_approved"),
            ("blocked", "review_approved"),
            ("failed", "review_approved"),
            ("test-sent", "review_approved"),
            ("unknown-sent", "review_approved"),
            ("formal-sent", "review_approved"),
            ("rejected", "review_rejected"),
        ]:
            insert_email_draft(
                connection,
                {"draft_status": draft_status},
                draft_id=draft_id,
            )

        for send_id, draft_id, status, mode in [
            ("send-blocked", "blocked", "blocked", "permission_check"),
            ("send-failed", "failed", "failed", "real_recipient"),
            ("send-test", "test-sent", "sent", "test_recipient"),
            ("send-unknown", "unknown-sent", "sent", None),
            ("send-formal", "formal-sent", "sent", "real_recipient"),
        ]:
            insert_email_send_log(
                connection,
                {
                    "send_id": send_id,
                    "draft_id": draft_id,
                    "status": status,
                    "send_mode": mode,
                },
            )

        summary = summarize_email_business_statuses(connection)

    assert summary[EMAIL_STATUS_PENDING_REVIEW] == 2
    assert summary[EMAIL_STATUS_READY_TO_SEND] == 5
    assert summary[EMAIL_STATUS_SENT] == 1
    assert summary[EMAIL_STATUS_REJECTED] == 1
    assert summary["formal_sent_count"] == 1
