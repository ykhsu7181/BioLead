"""Batch email draft, review, and controlled send services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
import sqlite3
from typing import Any

from scholarlead_agent.ai.email_drafts import email_draft_to_dict
from scholarlead_agent.background_jobs import (
    JOB_ITEM_STATUS_BLOCKED,
    JOB_ITEM_STATUS_COMPLETED,
    JOB_ITEM_STATUS_FAILED,
    JOB_TYPE_BATCH_DRAFT,
    JOB_TYPE_BATCH_SEND,
    JobItemSpec,
    block_job_item,
    claim_next_job_item,
    complete_job_item,
    create_job,
    fail_job_item,
    fetch_job,
    fetch_job_items,
    finalize_job_if_done,
    start_job,
)
from scholarlead_agent.config import AppConfig, load_config
from scholarlead_agent.database import (
    fetch_all,
    fetch_one,
    insert_email_draft,
    insert_email_review_record,
    insert_email_send_log,
)
from scholarlead_agent.email_review import (
    EmailReviewDecision,
    PermissionPolicy,
    apply_email_review_decision,
    build_email_audit_record,
    evaluate_send_permission,
)
from scholarlead_agent.email_sending import (
    EmailProvider,
    email_send_result_to_dict,
    send_reviewed_email,
)
from scholarlead_agent.email_smtp import (
    SmtpEmailProvider,
    build_email_send_policy_from_config,
    build_smtp_provider_config,
    send_reviewed_test_email,
)
from scholarlead_agent.pubmed_models import PubMedLead
from scholarlead_agent.services.email_draft_service import (
    EmailDraftGenerationError,
    EmailDraftService,
)


BATCH_SEND_MODE_PERMISSION_CHECK = "permission_check"
BATCH_SEND_MODE_TEST_RECIPIENT = "test_recipient"
BATCH_SEND_MODE_REAL_RECIPIENT = "real_recipient"
DEFAULT_BATCH_LIMIT = 50


@dataclass(frozen=True)
class BatchEmailDraftResult:
    """Summary for one batch draft generation job."""

    job_id: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    blocked_count: int
    draft_ids: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "blocked_count": self.blocked_count,
            "draft_ids": list(self.draft_ids),
            "errors": list(self.errors),
        }


@dataclass(frozen=True)
class BatchEmailReviewResult:
    """Summary for one batch review operation."""

    reviewed_count: int
    missing_count: int
    draft_ids: list[str] = field(default_factory=list)
    missing_draft_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewed_count": self.reviewed_count,
            "missing_count": self.missing_count,
            "draft_ids": list(self.draft_ids),
            "missing_draft_ids": list(self.missing_draft_ids),
        }


@dataclass(frozen=True)
class BatchEmailSendResult:
    """Summary for one controlled batch send job."""

    job_id: str
    status: str
    mode: str
    total_count: int
    sent_count: int
    failed_count: int
    blocked_count: int
    send_ids: list[str] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "mode": self.mode,
            "total_count": self.total_count,
            "sent_count": self.sent_count,
            "failed_count": self.failed_count,
            "blocked_count": self.blocked_count,
            "send_ids": list(self.send_ids),
            "errors": list(self.errors),
        }


def generate_batch_email_drafts(
    connection: sqlite3.Connection,
    *,
    lead_ids: list[str] | None = None,
    task_id: str | None = None,
    max_items: int = DEFAULT_BATCH_LIMIT,
    service: EmailDraftService | None = None,
    job_id: str | None = None,
) -> BatchEmailDraftResult:
    """Generate and persist review-pending drafts for selected leads."""

    normalized_max = _validate_max_items(max_items)
    leads = _select_leads(connection, lead_ids=lead_ids, task_id=task_id, max_items=normalized_max)
    job = create_job(
        connection,
        job_type=JOB_TYPE_BATCH_DRAFT,
        task_id=task_id,
        job_id=job_id,
        payload={"lead_ids": [lead.lead_id for lead in leads], "max_items": normalized_max},
        items=[JobItemSpec(lead_id=lead.lead_id) for lead in leads],
    )
    if not leads:
        finalized = finalize_job_if_done(connection, job.job_id)
        return _batch_draft_result(connection, finalized.job_id)

    draft_service = service or EmailDraftService()
    lead_by_id = {lead.lead_id: lead for lead in leads}
    start_job(connection, job.job_id)
    while True:
        item = claim_next_job_item(connection, job.job_id)
        if item is None:
            break
        if not item.lead_id or item.lead_id not in lead_by_id:
            block_job_item(connection, item.job_item_id, reason="lead_not_found")
            continue
        try:
            draft = draft_service.generate_for_lead(lead_by_id[item.lead_id])
            draft_data = email_draft_to_dict(draft)
            draft_id, draft_version, supersedes_draft_id = _next_draft_identity(
                connection,
                item.lead_id,
            )
            draft_data["draft_id"] = draft_id
            draft_data["draft_version"] = draft_version
            if supersedes_draft_id:
                draft_data["supersedes_draft_id"] = supersedes_draft_id
            insert_email_draft(connection, draft_data, draft_id=draft_id)
            complete_job_item(
                connection,
                item.job_item_id,
                result_payload={"draft_id": draft_id, "lead_id": item.lead_id},
            )
        except EmailDraftGenerationError as error:
            block_job_item(connection, item.job_item_id, reason=str(error))
        except Exception as error:
            fail_job_item(connection, item.job_item_id, error=str(error))
    finalize_job_if_done(connection, job.job_id)
    return _batch_draft_result(connection, job.job_id)


def apply_batch_email_review(
    connection: sqlite3.Connection,
    *,
    draft_ids: list[str],
    reviewer: str,
    decision: str,
    comments: str | None = None,
    policy: PermissionPolicy | None = None,
) -> BatchEmailReviewResult:
    """Apply the same human review decision to multiple drafts."""

    normalized_ids = _dedupe_required_ids(draft_ids, "draft_ids")
    reviewed: list[str] = []
    missing: list[str] = []
    for draft_id in normalized_ids:
        row = _fetch_draft_row(connection, draft_id)
        if row is None:
            missing.append(draft_id)
            continue
        draft = _draft_from_row(row)
        status_before = str(draft.get("draft_status") or "")
        updated = apply_email_review_decision(
            draft,
            EmailReviewDecision(
                reviewer=reviewer,
                decision=decision,
                comments=comments,
            ),
            policy=policy,
        )
        updated["draft_id"] = draft_id
        insert_email_draft(connection, updated, draft_id=draft_id)
        permission = evaluate_send_permission(updated, policy=policy)
        audit = build_email_audit_record(
            event_type="email_batch_review",
            lead_id=str(updated.get("lead_id") or ""),
            actor=reviewer,
            status_before=status_before,
            status_after=str(updated.get("draft_status") or ""),
            permission=permission,
            note=comments,
            metadata={"draft_id": draft_id, "decision": decision},
        )
        insert_email_review_record(connection, audit)
        reviewed.append(draft_id)
    return BatchEmailReviewResult(
        reviewed_count=len(reviewed),
        missing_count=len(missing),
        draft_ids=reviewed,
        missing_draft_ids=missing,
    )


def send_batch_reviewed_emails(
    connection: sqlite3.Connection,
    *,
    draft_ids: list[str],
    actor: str,
    mode: str = BATCH_SEND_MODE_PERMISSION_CHECK,
    max_items: int = 5,
    config: AppConfig | None = None,
    provider: EmailProvider | None = None,
    job_id: str | None = None,
) -> BatchEmailSendResult:
    """Run controlled batch send or permission checks for reviewed drafts."""

    normalized_ids = _dedupe_required_ids(draft_ids, "draft_ids")
    normalized_max = _validate_max_items(max_items)
    active_mode = _validate_send_mode(mode)
    selected_ids = normalized_ids[:normalized_max]
    rows = [_fetch_draft_row(connection, draft_id) for draft_id in selected_ids]
    draft_items = [
        (draft_id, _draft_from_row(row))
        for draft_id, row in zip(selected_ids, rows, strict=False)
        if row is not None
    ]
    missing = [draft_id for draft_id, row in zip(selected_ids, rows, strict=False) if row is None]
    job = create_job(
        connection,
        job_type=JOB_TYPE_BATCH_SEND,
        job_id=job_id,
        payload={"draft_ids": selected_ids, "mode": active_mode, "missing_draft_ids": missing},
        items=[
            JobItemSpec(
                lead_id=str(draft.get("lead_id") or None),
                payload={"draft_id": draft_id, "mode": active_mode},
            )
            for draft_id, draft in draft_items
        ],
    )
    if not draft_items:
        finalize_job_if_done(connection, job.job_id)
        return _batch_send_result(connection, job.job_id, active_mode)

    draft_by_id = {draft_id: draft for draft_id, draft in draft_items}
    active_config = config or load_config()
    active_provider = provider
    if active_mode == BATCH_SEND_MODE_REAL_RECIPIENT and active_provider is None:
        smtp_config = build_smtp_provider_config(active_config)
        if smtp_config.configured:
            active_provider = SmtpEmailProvider(smtp_config)
    start_job(connection, job.job_id)
    while True:
        item = claim_next_job_item(connection, job.job_id)
        if item is None:
            break
        draft_id = str(item.payload.get("draft_id") or "")
        draft = draft_by_id.get(draft_id)
        if draft is None:
            block_job_item(connection, item.job_item_id, reason="draft_not_found")
            continue
        try:
            result_data = _send_or_check_one(
                draft,
                draft_id=draft_id,
                actor=actor,
                mode=active_mode,
                config=active_config,
                provider=active_provider,
                connection=connection,
            )
            insert_email_send_log(connection, result_data)
            if result_data["status"] == "sent":
                complete_job_item(connection, item.job_item_id, result_payload=result_data)
            elif result_data["status"] == "blocked":
                block_job_item(connection, item.job_item_id, reason=result_data.get("error_message") or "blocked")
            else:
                fail_job_item(connection, item.job_item_id, error=result_data.get("error_message") or "failed")
        except Exception as error:
            fail_job_item(connection, item.job_item_id, error=str(error))
    finalize_job_if_done(connection, job.job_id)
    return _batch_send_result(connection, job.job_id, active_mode)


def count_email_sends_today(connection: sqlite3.Connection) -> int:
    """Count successful send logs for the local date."""

    today = date.today().isoformat()
    row = connection.execute(
        """
        SELECT COUNT(*) AS count
        FROM email_send_logs
        WHERE status = 'sent' AND substr(attempted_at, 1, 10) = ?
        """,
        (today,),
    ).fetchone()
    return int(row["count"] if row is not None else 0)


def _send_or_check_one(
    draft: dict[str, Any],
    *,
    draft_id: str,
    actor: str,
    mode: str,
    config: AppConfig,
    provider: EmailProvider | None,
    connection: sqlite3.Connection,
) -> dict[str, Any]:
    sent_today = count_email_sends_today(connection)
    if mode == BATCH_SEND_MODE_PERMISSION_CHECK:
        policy = build_email_send_policy_from_config(config, sent_today=sent_today)
        result = send_reviewed_email(
            draft,
            actor=actor,
            policy=policy,
            provider=None,
            draft_id=draft_id,
            extra_blockers=["permission_check_only"],
        )
    elif mode == BATCH_SEND_MODE_TEST_RECIPIENT:
        result = send_reviewed_test_email(
            draft,
            actor=actor,
            config=config,
            provider=provider if isinstance(provider, SmtpEmailProvider) else None,
            draft_id=draft_id,
            sent_today=sent_today,
        )
    else:
        policy = build_email_send_policy_from_config(config, sent_today=sent_today)
        result = send_reviewed_email(
            draft,
            actor=actor,
            policy=policy,
            provider=provider,
            draft_id=draft_id,
        )
    result_data = email_send_result_to_dict(result)
    result_data["send_mode"] = mode
    if result_data.get("audit_record"):
        insert_email_review_record(connection, result_data["audit_record"])
    return result_data


def _select_leads(
    connection: sqlite3.Connection,
    *,
    lead_ids: list[str] | None,
    task_id: str | None,
    max_items: int,
) -> list[PubMedLead]:
    if lead_ids:
        normalized_ids = _dedupe_required_ids(lead_ids, "lead_ids")
        if len(normalized_ids) > max_items:
            raise ValueError("lead_ids count must not exceed max_items")
        placeholders = ",".join("?" for _ in normalized_ids)
        rows = fetch_all(
            connection,
            f"SELECT * FROM leads WHERE lead_id IN ({placeholders}) ORDER BY updated_at DESC",
            tuple(normalized_ids),
        )
        by_id = {str(row["lead_id"]): row for row in rows}
        return [
            _lead_from_row(by_id[lead_id])
            for lead_id in normalized_ids
            if lead_id in by_id
        ]
    if task_id:
        rows = fetch_all(
            connection,
            """
            SELECT l.*
            FROM lead_discoveries AS d
            JOIN leads AS l ON l.lead_id = d.lead_id
            WHERE d.task_id = ?
            ORDER BY d.discovered_at DESC, l.lead_id DESC
            LIMIT ?
            """,
            (task_id, max_items),
        )
    else:
        rows = fetch_all(
            connection,
            "SELECT * FROM leads ORDER BY updated_at DESC, lead_id DESC LIMIT ?",
            (max_items,),
        )
    return [_lead_from_row(row) for row in rows]


def _lead_from_row(row: sqlite3.Row) -> PubMedLead:
    payload = json.loads(row["payload_json"] or "{}")
    return PubMedLead(**payload)


def _fetch_draft_row(connection: sqlite3.Connection, draft_id: str) -> sqlite3.Row | None:
    return fetch_one(connection, "SELECT * FROM email_drafts WHERE draft_id = ?", (draft_id,))


def _next_draft_identity(
    connection: sqlite3.Connection,
    lead_id: str,
) -> tuple[str, str, str | None]:
    """Return a new draft identity so batch regeneration never overwrites history."""

    base_id = f"draft-{lead_id}"
    rows = fetch_all(
        connection,
        "SELECT draft_id FROM email_drafts WHERE lead_id = ? ORDER BY created_at, draft_id",
        (lead_id,),
    )
    if not rows:
        return base_id, "v1", None

    existing_ids = {str(row["draft_id"]) for row in rows}
    version_number = 2
    while f"{base_id}-v{version_number}" in existing_ids:
        version_number += 1
    return f"{base_id}-v{version_number}", f"v{version_number}", str(rows[-1]["draft_id"])


def _draft_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    payload = json.loads(data.pop("payload_json", "{}") or "{}")
    payload.setdefault("draft_id", data.get("draft_id"))
    payload.setdefault("lead_id", data.get("lead_id"))
    payload.setdefault("verified_email", data.get("verified_email"))
    payload.setdefault("recipient_name", data.get("recipient_name"))
    payload.setdefault("subject", data.get("subject"))
    payload.setdefault("body", data.get("body"))
    payload.setdefault("language", data.get("language"))
    payload.setdefault("draft_status", data.get("draft_status"))
    payload.setdefault("human_reviewer", data.get("human_reviewer"))
    payload.setdefault("reviewed_at", data.get("reviewed_at"))
    payload.setdefault("can_send", bool(data.get("can_send")))
    return payload


def _batch_draft_result(connection: sqlite3.Connection, job_id: str) -> BatchEmailDraftResult:
    job = fetch_job(connection, job_id)
    items = fetch_job_items(connection, job_id)
    draft_ids: list[str] = []
    errors: list[dict[str, Any]] = []
    for item in items:
        draft_id = item.payload.get("result", {}).get("draft_id")
        if draft_id:
            draft_ids.append(str(draft_id))
        if item.status in {JOB_ITEM_STATUS_FAILED, JOB_ITEM_STATUS_BLOCKED}:
            errors.append({"lead_id": item.lead_id, "status": item.status, "error": item.error})
    return BatchEmailDraftResult(
        job_id=job.job_id,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        blocked_count=job.blocked_count,
        draft_ids=draft_ids,
        errors=errors,
    )


def _batch_send_result(connection: sqlite3.Connection, job_id: str, mode: str) -> BatchEmailSendResult:
    job = fetch_job(connection, job_id)
    items = fetch_job_items(connection, job_id)
    send_ids: list[str] = []
    errors: list[dict[str, Any]] = []
    for item in items:
        send_id = item.payload.get("result", {}).get("send_id")
        if send_id:
            send_ids.append(str(send_id))
        if item.status in {JOB_ITEM_STATUS_FAILED, JOB_ITEM_STATUS_BLOCKED}:
            errors.append(
                {
                    "draft_id": item.payload.get("draft_id"),
                    "lead_id": item.lead_id,
                    "status": item.status,
                    "error": item.error,
                }
            )
    return BatchEmailSendResult(
        job_id=job.job_id,
        status=job.status,
        mode=mode,
        total_count=job.total_count,
        sent_count=job.success_count,
        failed_count=job.failed_count,
        blocked_count=job.blocked_count,
        send_ids=send_ids,
        errors=errors,
    )


def _validate_max_items(value: int) -> int:
    if value < 1:
        raise ValueError("max_items must be at least 1")
    if value > DEFAULT_BATCH_LIMIT:
        raise ValueError(f"max_items must be <= {DEFAULT_BATCH_LIMIT}")
    return value


def _validate_send_mode(mode: str) -> str:
    normalized = (mode or "").strip().lower()
    if normalized not in {
        BATCH_SEND_MODE_PERMISSION_CHECK,
        BATCH_SEND_MODE_TEST_RECIPIENT,
        BATCH_SEND_MODE_REAL_RECIPIENT,
    }:
        raise ValueError("mode must be permission_check, test_recipient, or real_recipient")
    return normalized


def _dedupe_required_ids(values: list[str], field_name: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in seen:
            normalized.append(cleaned)
            seen.add(cleaned)
    if not normalized:
        raise ValueError(f"{field_name} cannot be empty")
    return normalized
