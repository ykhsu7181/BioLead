"""Shared business-status rules for reviewed email drafts and send attempts."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import json
import sqlite3
from typing import Any


EMAIL_STATUS_PENDING_REVIEW = "pending_review"
EMAIL_STATUS_READY_TO_SEND = "ready_to_send"
EMAIL_STATUS_SENT = "sent"
EMAIL_STATUS_REJECTED = "rejected"
EMAIL_STATUS_UNKNOWN = "unknown"

SEND_MODE_PERMISSION_CHECK = "permission_check"
SEND_MODE_TEST_RECIPIENT = "test_recipient"
SEND_MODE_REAL_RECIPIENT = "real_recipient"
SEND_MODE_UNKNOWN = "unknown"

_PENDING_DRAFT_STATUSES = {"review_pending", "changes_requested"}
_KNOWN_SEND_MODES = {
    SEND_MODE_PERMISSION_CHECK,
    SEND_MODE_TEST_RECIPIENT,
    SEND_MODE_REAL_RECIPIENT,
}


def resolve_email_business_status(
    draft_status: str | None,
    send_records: Iterable[Mapping[str, Any]] = (),
) -> str:
    """Return the shared business status for one draft and its send history."""

    records = list(send_records)
    if any(describe_send_record(record)["is_formal_send_success"] for record in records):
        return EMAIL_STATUS_SENT

    normalized_status = _clean(draft_status)
    if normalized_status in _PENDING_DRAFT_STATUSES:
        return EMAIL_STATUS_PENDING_REVIEW
    if normalized_status == "review_approved":
        return EMAIL_STATUS_READY_TO_SEND
    if normalized_status == "review_rejected":
        return EMAIL_STATUS_REJECTED
    return EMAIL_STATUS_UNKNOWN


def get_send_mode(record: Mapping[str, Any]) -> str:
    """Read a persisted send mode without guessing legacy records."""

    direct_mode = _clean(record.get("send_mode"))
    if direct_mode in _KNOWN_SEND_MODES:
        return direct_mode

    payload = record.get("payload")
    if not isinstance(payload, Mapping):
        payload = _parse_payload(record.get("payload_json"))
    payload_mode = _clean(payload.get("send_mode")) if isinstance(payload, Mapping) else ""
    return payload_mode if payload_mode in _KNOWN_SEND_MODES else SEND_MODE_UNKNOWN


def describe_send_record(record: Mapping[str, Any]) -> dict[str, str | bool]:
    """Return stable display and reporting metadata for one send attempt."""

    mode = get_send_mode(record)
    status = _clean(record.get("status")) or "unknown"
    succeeded = status == "sent"

    if mode == SEND_MODE_PERMISSION_CHECK:
        label = "权限检查"
        category = "permission_check"
    elif mode == SEND_MODE_TEST_RECIPIENT:
        label = "测试发送成功" if succeeded else "测试发送失败"
        category = "test_send"
    elif mode == SEND_MODE_REAL_RECIPIENT:
        label = "正式发送成功" if succeeded else "正式发送失败"
        category = "formal_send"
    else:
        label = "未知发送类型"
        category = "unknown"

    return {
        "send_mode": mode,
        "send_category": category,
        "send_label": label,
        "is_formal_send_success": mode == SEND_MODE_REAL_RECIPIENT and succeeded,
    }


def summarize_email_business_statuses(connection: sqlite3.Connection) -> dict[str, int]:
    """Count draft business statuses and formal sends from persisted records."""

    send_rows = connection.execute(
        "SELECT draft_id, status, payload_json FROM email_send_logs"
    ).fetchall()
    sends_by_draft: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    formal_sent_count = 0
    for row in send_rows:
        record = dict(row)
        draft_id = str(record.get("draft_id") or "")
        if draft_id:
            sends_by_draft[draft_id].append(record)
        if describe_send_record(record)["is_formal_send_success"]:
            formal_sent_count += 1

    counts: Counter[str] = Counter()
    draft_rows = connection.execute(
        "SELECT draft_id, draft_status FROM email_drafts"
    ).fetchall()
    for row in draft_rows:
        draft_id = str(row["draft_id"])
        status = resolve_email_business_status(
            row["draft_status"],
            sends_by_draft.get(draft_id, ()),
        )
        counts[status] += 1

    return {
        EMAIL_STATUS_PENDING_REVIEW: counts[EMAIL_STATUS_PENDING_REVIEW],
        EMAIL_STATUS_READY_TO_SEND: counts[EMAIL_STATUS_READY_TO_SEND],
        EMAIL_STATUS_SENT: counts[EMAIL_STATUS_SENT],
        EMAIL_STATUS_REJECTED: counts[EMAIL_STATUS_REJECTED],
        EMAIL_STATUS_UNKNOWN: counts[EMAIL_STATUS_UNKNOWN],
        "formal_sent_count": formal_sent_count,
    }


def _parse_payload(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def _clean(value: Any) -> str:
    return str(value or "").strip().lower()
