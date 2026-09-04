"""SQLite foundation for ScholarLead Agent productization.

Stage 24 introduces a small database layer without replacing the existing raw
and processed file exports. The database stores normalized summaries and JSON
payloads for later product workflows.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from scholarlead_agent.ai.email_drafts import EmailDraft, email_draft_to_dict
from scholarlead_agent.ai.usage import AIUsageRecord, ai_usage_record_to_dict
from scholarlead_agent.agent.conversation import (
    ConversationMessage,
    TaskContext,
)
from scholarlead_agent.email_review import (
    EmailAuditRecord,
    email_audit_record_to_dict,
)
from scholarlead_agent.pubmed_models import PubMedLead, PubMedPaper
from scholarlead_agent.unified_models import EvidenceRecord


DATABASE_SCHEMA_VERSION = 6

LEAD_DISCOVERY_STATUSES = {
    "new_record",
    "repeat_record",
    "legacy_unknown",
}

EXPECTED_TABLES = {
    "schema_migrations",
    "conversations",
    "conversation_messages",
    "conversation_state",
    "tasks",
    "papers",
    "paper_discoveries",
    "researchers",
    "organizations",
    "contacts",
    "funding_records",
    "leads",
    "lead_discoveries",
    "evidence_records",
    "email_drafts",
    "email_reviews",
    "email_send_logs",
    "ai_usage",
    "tool_calls",
    "run_reports",
    "jobs",
    "job_items",
    "settings",
    "agent_run_idempotency",
}


def connect_database(path: Path | str) -> sqlite3.Connection:
    """Open a SQLite connection with project defaults."""

    db_path = Path(path)
    if str(db_path) != ":memory:":
        db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path | str) -> sqlite3.Connection:
    """Create or migrate the Stage 24 database and return a connection."""

    connection = connect_database(path)
    apply_schema(connection)
    return connection


def apply_schema(connection: sqlite3.Connection) -> None:
    """Apply the current SQLite schema idempotently."""

    try:
        connection.execute("BEGIN IMMEDIATE")
        _execute_schema_script(connection, _SCHEMA_SQL)
        _backfill_discovery_history(connection)
        _validate_discovery_history(connection)
        connection.execute(f"PRAGMA user_version = {DATABASE_SCHEMA_VERSION}")
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(version, applied_at)
            VALUES (?, ?)
            """,
            (DATABASE_SCHEMA_VERSION, _now()),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return SQLite user_version for the current database."""

    row = connection.execute("PRAGMA user_version").fetchone()
    return int(row[0])


def list_tables(connection: sqlite3.Connection) -> set[str]:
    """Return user table names in the current database."""

    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {str(row["name"]) for row in rows}


def insert_conversation(
    connection: sqlite3.Connection,
    *,
    conversation_id: str,
    title: str | None = None,
    status: str = "active",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Insert or update one conversation summary."""

    if not _clean(conversation_id):
        raise ValueError("conversation_id cannot be empty")
    now = _now()
    connection.execute(
        """
        INSERT INTO conversations (
            conversation_id, title, status, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            title = excluded.title,
            status = excluded.status,
            metadata_json = excluded.metadata_json,
            updated_at = excluded.updated_at
        """,
        (
            conversation_id,
            title,
            status,
            _json(metadata or {}),
            now,
            now,
        ),
    )
    connection.commit()


def insert_conversation_message(
    connection: sqlite3.Connection,
    message: ConversationMessage,
) -> None:
    """Insert one conversation message."""

    if not _clean(message.message_id):
        raise ValueError("message_id cannot be empty")
    if not _clean(message.conversation_id):
        raise ValueError("conversation_id cannot be empty")
    connection.execute(
        """
        INSERT OR REPLACE INTO conversation_messages (
            message_id, conversation_id, role, content, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            message.message_id,
            message.conversation_id,
            message.role,
            message.content,
            _json(message.metadata),
            message.created_at,
        ),
    )
    connection.commit()


def upsert_conversation_state(
    connection: sqlite3.Connection,
    context: TaskContext,
) -> None:
    """Insert or update the minimal task context for a conversation."""

    if not _clean(context.conversation_id):
        raise ValueError("conversation_id cannot be empty")
    updated_at = context.updated_at or _now()
    connection.execute(
        """
        INSERT INTO conversation_state (
            conversation_id, task_id, last_run_report_path, last_lead_ids_json,
            last_selected_lead_ids_json, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(conversation_id) DO UPDATE SET
            task_id = excluded.task_id,
            last_run_report_path = excluded.last_run_report_path,
            last_lead_ids_json = excluded.last_lead_ids_json,
            last_selected_lead_ids_json = excluded.last_selected_lead_ids_json,
            updated_at = excluded.updated_at
        """,
        (
            context.conversation_id,
            context.task_id,
            context.last_run_report_path,
            _json(context.last_lead_ids),
            _json(context.last_selected_lead_ids),
            updated_at,
        ),
    )
    connection.commit()


def fetch_conversation_messages(
    connection: sqlite3.Connection,
    conversation_id: str,
    *,
    limit: int = 20,
) -> list[ConversationMessage]:
    """Fetch recent messages for a conversation in chronological order."""

    rows = connection.execute(
        """
        SELECT * FROM conversation_messages
        WHERE conversation_id = ?
        ORDER BY created_at DESC, message_id DESC
        LIMIT ?
        """,
        (conversation_id, limit),
    ).fetchall()
    messages = [
        ConversationMessage(
            message_id=str(row["message_id"]),
            conversation_id=str(row["conversation_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
        )
        for row in rows
    ]
    return list(reversed(messages))


def fetch_task_context(
    connection: sqlite3.Connection,
    conversation_id: str,
) -> TaskContext | None:
    """Fetch the latest task context for a conversation."""

    row = connection.execute(
        "SELECT * FROM conversation_state WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    if row is None:
        return None
    return TaskContext(
        conversation_id=str(row["conversation_id"]),
        task_id=row["task_id"],
        last_run_report_path=row["last_run_report_path"],
        last_lead_ids=json.loads(row["last_lead_ids_json"] or "[]"),
        last_selected_lead_ids=json.loads(row["last_selected_lead_ids_json"] or "[]"),
        updated_at=str(row["updated_at"]),
    )


def insert_task(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    task_type: str,
    status: str,
    query: str | None = None,
    parameters: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    run_report_path: str | None = None,
    _commit: bool = True,
) -> None:
    """Insert or update one task summary."""

    if not _clean(task_id):
        raise ValueError("task_id cannot be empty")
    if not _clean(task_type):
        raise ValueError("task_type cannot be empty")

    now = _now()
    connection.execute(
        """
        INSERT INTO tasks (
            task_id, task_type, query, status, parameters_json, started_at,
            finished_at, run_report_path, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
            task_type = excluded.task_type,
            query = excluded.query,
            status = excluded.status,
            parameters_json = excluded.parameters_json,
            started_at = excluded.started_at,
            finished_at = excluded.finished_at,
            run_report_path = excluded.run_report_path,
            updated_at = excluded.updated_at
        """,
        (
            task_id,
            task_type,
            query,
            status,
            _json(parameters or {}),
            started_at,
            finished_at,
            run_report_path,
            now,
            now,
        ),
    )
    if _commit:
        connection.commit()


def insert_pubmed_paper(
    connection: sqlite3.Connection,
    paper: PubMedPaper,
    *,
    task_id: str | None = None,
    discovered_at: str | None = None,
    _commit: bool = True,
) -> None:
    """Insert or update one PubMed paper summary."""

    paper_id = f"pubmed:{paper.pmid}"
    source_id = paper.pmid
    now = _now()
    try:
        connection.execute(
            """
            INSERT INTO papers (
            paper_id, task_id, source, source_id, pmid, doi, title, abstract,
            journal, publisher, publication_date, publication_year, authors_json,
            organizations_json, source_url, raw_record_path, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
            task_id = excluded.task_id,
            doi = excluded.doi,
            title = excluded.title,
            abstract = excluded.abstract,
            journal = excluded.journal,
            publication_date = excluded.publication_date,
            publication_year = excluded.publication_year,
            authors_json = excluded.authors_json,
            organizations_json = excluded.organizations_json,
            source_url = excluded.source_url,
            raw_record_path = excluded.raw_record_path,
            updated_at = excluded.updated_at
            """,
            (
                paper_id,
                task_id,
                paper.source,
                source_id,
                paper.pmid,
                paper.doi,
                paper.title,
                paper.abstract,
                paper.journal,
                None,
                paper.publication_date,
                paper.publication_year,
                _json([author.full_name for author in paper.authors]),
                _json(paper.affiliations),
                paper.source_url,
                paper.raw_record_path,
                now,
                now,
            ),
        )
        if task_id is not None:
            record_paper_discovery(
                connection,
                task_id=task_id,
                paper_id=paper_id,
                source=paper.source,
                discovered_at=discovered_at or now,
                source_record_id=source_id,
                _commit=False,
            )
        if _commit:
            connection.commit()
    except Exception:
        if _commit:
            connection.rollback()
        raise


def insert_pubmed_lead(
    connection: sqlite3.Connection,
    lead: PubMedLead,
    *,
    task_id: str | None = None,
    discovered_at: str | None = None,
    _commit: bool = True,
) -> None:
    """Insert or update one PubMed lead summary."""

    now = _now()
    lead_exists = connection.execute(
        "SELECT 1 FROM leads WHERE lead_id = ?",
        (lead.lead_id,),
    ).fetchone() is not None
    try:
        connection.execute(
            """
            INSERT INTO leads (
            lead_id, task_id, pi_full_name, verified_email, email_status,
            institution, country, priority, lead_score, pmid, doi, data_quality,
            manual_review_required, raw_affiliation, payload_json, created_at,
            updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id) DO UPDATE SET
            task_id = excluded.task_id,
            pi_full_name = excluded.pi_full_name,
            verified_email = excluded.verified_email,
            email_status = excluded.email_status,
            institution = excluded.institution,
            country = excluded.country,
            priority = excluded.priority,
            lead_score = excluded.lead_score,
            pmid = excluded.pmid,
            doi = excluded.doi,
            data_quality = excluded.data_quality,
            manual_review_required = excluded.manual_review_required,
            raw_affiliation = excluded.raw_affiliation,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
            """,
            (
                lead.lead_id,
                task_id,
                lead.pi_full_name,
                lead.verified_email,
                lead.email_status,
                lead.institution,
                lead.country,
                lead.priority,
                lead.lead_score,
                lead.pmid,
                lead.doi,
                lead.data_quality,
                int(lead.manual_review_required),
                lead.raw_affiliation,
                _json(asdict(lead)),
                now,
                now,
            ),
        )
        if task_id is not None:
            record_lead_discovery(
                connection,
                task_id=task_id,
                lead_id=lead.lead_id,
                source="pubmed",
                discovered_at=discovered_at or now,
                discovery_status="repeat_record" if lead_exists else "new_record",
                source_record_id=lead.pmid,
                _commit=False,
            )
        if _commit:
            connection.commit()
    except Exception:
        if _commit:
            connection.rollback()
        raise


def record_lead_discovery(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    lead_id: str,
    source: str,
    discovered_at: str,
    discovery_status: str,
    source_record_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    _commit: bool = True,
) -> bool:
    """Record one idempotent Task-to-Lead discovery relationship."""

    if not _clean(task_id):
        raise ValueError("task_id cannot be empty")
    if not _clean(lead_id):
        raise ValueError("lead_id cannot be empty")
    if not _clean(source):
        raise ValueError("source cannot be empty")
    if not _clean(discovered_at):
        raise ValueError("discovered_at cannot be empty")
    if discovery_status not in LEAD_DISCOVERY_STATUSES:
        raise ValueError(f"unsupported discovery_status: {discovery_status}")
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO lead_discoveries (
            task_id, lead_id, source, discovered_at, discovery_status,
            source_record_id, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            lead_id,
            source,
            discovered_at,
            discovery_status,
            source_record_id,
            _json(metadata or {}),
            _now(),
        ),
    )
    if _commit:
        connection.commit()
    return cursor.rowcount > 0


def record_paper_discovery(
    connection: sqlite3.Connection,
    *,
    task_id: str,
    paper_id: str,
    source: str,
    discovered_at: str,
    source_record_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    _commit: bool = True,
) -> bool:
    """Record one idempotent Task-to-Paper discovery relationship."""

    for field_name, value in (
        ("task_id", task_id),
        ("paper_id", paper_id),
        ("source", source),
        ("discovered_at", discovered_at),
    ):
        if not _clean(value):
            raise ValueError(f"{field_name} cannot be empty")
    cursor = connection.execute(
        """
        INSERT OR IGNORE INTO paper_discoveries (
            task_id, paper_id, source, discovered_at, source_record_id,
            metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id,
            paper_id,
            source,
            discovered_at,
            source_record_id,
            _json(metadata or {}),
            _now(),
        ),
    )
    if _commit:
        connection.commit()
    return cursor.rowcount > 0


def fetch_task_lead_ids(
    connection: sqlite3.Connection,
    task_id: str,
) -> list[str]:
    """Return Lead IDs discovered by one task in stable discovery order."""

    rows = connection.execute(
        """
        SELECT lead_id FROM lead_discoveries
        WHERE task_id = ?
        ORDER BY discovered_at, lead_id
        """,
        (task_id,),
    ).fetchall()
    return [str(row["lead_id"]) for row in rows]


def fetch_task_paper_ids(
    connection: sqlite3.Connection,
    task_id: str,
) -> list[str]:
    """Return Paper IDs discovered by one task in stable discovery order."""

    rows = connection.execute(
        """
        SELECT paper_id FROM paper_discoveries
        WHERE task_id = ?
        ORDER BY discovered_at, paper_id
        """,
        (task_id,),
    ).fetchall()
    return [str(row["paper_id"]) for row in rows]


def fetch_lead_discoveries(
    connection: sqlite3.Connection,
    lead_id: str,
) -> list[dict[str, Any]]:
    """Return all discovery records for one Lead, newest first."""

    return fetch_all(
        connection,
        """
        SELECT * FROM lead_discoveries
        WHERE lead_id = ?
        ORDER BY discovered_at DESC, task_id DESC
        """,
        (lead_id,),
    )


def persist_pubmed_run_result(
    connection: sqlite3.Connection,
    result: Any,
) -> None:
    """Persist a PubMedRunResult-like object into Stage 24 tables."""

    params = result.search_params
    discovered_at = result.finished_at or _now()
    try:
        insert_task(
            connection,
            task_id=result.task_id,
            task_type="pubmed_search",
            query=params.query,
            status=result.status,
            parameters=asdict(params),
            started_at=result.started_at,
            finished_at=result.finished_at,
            run_report_path=str(result.run_report_path),
            _commit=False,
        )
        for paper in result.papers:
            insert_pubmed_paper(
                connection,
                paper,
                task_id=result.task_id,
                discovered_at=discovered_at,
                _commit=False,
            )
        for lead in result.leads:
            insert_pubmed_lead(
                connection,
                lead,
                task_id=result.task_id,
                discovered_at=discovered_at,
                _commit=False,
            )
        insert_run_report(
            connection,
            report_id=f"{result.task_id}:run_report",
            task_id=result.task_id,
            source="pubmed",
            status=result.status,
            run_report_path=str(result.run_report_path),
            report=result.run_report,
            _commit=False,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def claim_agent_run_idempotency(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    request_fingerprint: str,
) -> dict[str, Any]:
    """Claim an Agent run key or return its prior state."""

    key = _clean(idempotency_key)
    if not key:
        raise ValueError("idempotency_key cannot be empty")

    row = connection.execute(
        "SELECT * FROM agent_run_idempotency WHERE idempotency_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        now = _now()
        connection.execute(
            """
            INSERT INTO agent_run_idempotency (
                idempotency_key, request_fingerprint, status, response_json,
                created_at, updated_at
            )
            VALUES (?, ?, 'in_progress', NULL, ?, ?)
            """,
            (key, request_fingerprint, now, now),
        )
        connection.commit()
        return {"state": "claimed"}

    record = dict(row)
    if record["request_fingerprint"] != request_fingerprint:
        return {"state": "conflict"}
    if record["status"] == "completed" and record["response_json"]:
        return {
            "state": "completed",
            "response": json.loads(record["response_json"]),
        }
    if record["status"] == "in_progress":
        return {"state": "in_progress"}

    connection.execute(
        """
        UPDATE agent_run_idempotency
        SET status = 'in_progress', response_json = NULL, updated_at = ?
        WHERE idempotency_key = ?
        """,
        (_now(), key),
    )
    connection.commit()
    return {"state": "claimed"}


def complete_agent_run_idempotency(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
    response: dict[str, Any],
) -> None:
    """Store the completed public Agent response for a retry."""

    connection.execute(
        """
        UPDATE agent_run_idempotency
        SET status = 'completed', response_json = ?, updated_at = ?
        WHERE idempotency_key = ?
        """,
        (_json(response), _now(), idempotency_key),
    )
    connection.commit()


def fail_agent_run_idempotency(
    connection: sqlite3.Connection,
    *,
    idempotency_key: str,
) -> None:
    """Mark a failed Agent run key retryable without storing internal errors."""

    connection.execute(
        """
        UPDATE agent_run_idempotency
        SET status = 'failed', updated_at = ?
        WHERE idempotency_key = ?
        """,
        (_now(), idempotency_key),
    )
    connection.commit()


def insert_evidence_record(
    connection: sqlite3.Connection,
    evidence: EvidenceRecord,
    *,
    evidence_id: str | None = None,
) -> str:
    """Insert one evidence record and return its database id."""

    row_id = evidence_id or str(uuid4())
    connection.execute(
        """
        INSERT OR REPLACE INTO evidence_records (
            evidence_id, source_name, source_type, source_id, source_url,
            retrieved_at, field_name, field_value, confidence, raw_record_path,
            note, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row_id,
            evidence.source_name,
            evidence.source_type,
            evidence.source_id,
            evidence.source_url,
            evidence.retrieved_at,
            evidence.field_name,
            evidence.field_value,
            evidence.confidence,
            evidence.raw_record_path,
            evidence.note,
            _now(),
        ),
    )
    connection.commit()
    return row_id


def insert_email_draft(
    connection: sqlite3.Connection,
    draft: EmailDraft | dict[str, Any],
    *,
    draft_id: str | None = None,
) -> str:
    """Insert or update one email draft summary."""

    data = email_draft_to_dict(draft) if isinstance(draft, EmailDraft) else dict(draft)
    row_id = draft_id or str(data.get("draft_id") or uuid4())
    now = _now()
    connection.execute(
        """
        INSERT INTO email_drafts (
            draft_id, lead_id, recipient_name, verified_email, subject, body,
            language, draft_status, human_reviewer, reviewed_at, can_send,
            payload_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(draft_id) DO UPDATE SET
            lead_id = excluded.lead_id,
            recipient_name = excluded.recipient_name,
            verified_email = excluded.verified_email,
            subject = excluded.subject,
            body = excluded.body,
            language = excluded.language,
            draft_status = excluded.draft_status,
            human_reviewer = excluded.human_reviewer,
            reviewed_at = excluded.reviewed_at,
            can_send = excluded.can_send,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
        """,
        (
            row_id,
            data.get("lead_id"),
            data.get("recipient_name"),
            data.get("verified_email"),
            data.get("subject"),
            data.get("body"),
            data.get("language"),
            data.get("draft_status"),
            data.get("human_reviewer"),
            data.get("reviewed_at"),
            int(bool(data.get("can_send"))),
            _json(data),
            now,
            now,
        ),
    )
    connection.commit()
    return row_id


def insert_email_review_record(
    connection: sqlite3.Connection,
    record: EmailAuditRecord | dict[str, Any],
) -> None:
    """Insert one email review or permission audit record."""

    data = (
        email_audit_record_to_dict(record)
        if isinstance(record, EmailAuditRecord)
        else dict(record)
    )
    connection.execute(
        """
        INSERT OR REPLACE INTO email_reviews (
            event_id, event_type, lead_id, actor, occurred_at, status_before,
            status_after, permission_allowed, permission_blockers_json, note,
            metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("event_id"),
            data.get("event_type"),
            data.get("lead_id"),
            data.get("actor"),
            data.get("occurred_at"),
            data.get("status_before"),
            data.get("status_after"),
            _optional_bool(data.get("permission_allowed")),
            _json(data.get("permission_blockers") or []),
            data.get("note"),
            _json(data.get("metadata") or {}),
        ),
    )
    connection.commit()


def insert_email_send_log(
    connection: sqlite3.Connection,
    result: dict[str, Any],
) -> None:
    """Insert one email send attempt, including blocked and failed attempts."""

    connection.execute(
        """
        INSERT OR REPLACE INTO email_send_logs (
            send_id, draft_id, lead_id, recipient_email, provider, status,
            provider_message_id, attempted_at, finished_at, actor,
            permission_allowed, permission_blockers_json, permission_warnings_json,
            error_type, error_message, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.get("send_id"),
            result.get("draft_id"),
            result.get("lead_id"),
            result.get("recipient_email"),
            result.get("provider"),
            result.get("status"),
            result.get("provider_message_id"),
            result.get("attempted_at"),
            result.get("finished_at"),
            result.get("actor"),
            _optional_bool(result.get("permission_allowed")),
            _json(result.get("permission_blockers") or []),
            _json(result.get("permission_warnings") or []),
            result.get("error_type"),
            result.get("error_message"),
            _json(result),
        ),
    )
    connection.commit()


def insert_ai_usage_record(
    connection: sqlite3.Connection,
    record: AIUsageRecord | dict[str, Any],
) -> None:
    """Insert or update one AI usage record."""

    data = ai_usage_record_to_dict(record) if isinstance(record, AIUsageRecord) else dict(record)
    connection.execute(
        """
        INSERT OR REPLACE INTO ai_usage (
            usage_id, account_alias, provider, called_at, feature_module,
            model_name, input_tokens, output_tokens, total_tokens, estimated_cost,
            currency, pricing_config_version, status, error_type, error_message,
            task_id, lead_id, started_at, finished_at, latency_ms
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("usage_id"),
            data.get("account_alias"),
            data.get("provider"),
            data.get("called_at"),
            data.get("feature_module"),
            data.get("model_name"),
            data.get("input_tokens"),
            data.get("output_tokens"),
            data.get("total_tokens"),
            data.get("estimated_cost"),
            data.get("currency"),
            data.get("pricing_config_version"),
            data.get("status"),
            data.get("error_type"),
            data.get("error_message"),
            data.get("task_id"),
            data.get("lead_id"),
            data.get("started_at"),
            data.get("finished_at"),
            data.get("latency_ms"),
        ),
    )
    connection.commit()


def insert_tool_call(
    connection: sqlite3.Connection,
    *,
    tool_call_id: str,
    task_id: str | None,
    tool_name: str,
    source: str | None,
    success: bool,
    arguments: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    """Insert one Agent tool-call log row."""

    connection.execute(
        """
        INSERT OR REPLACE INTO tool_calls (
            tool_call_id, task_id, tool_name, source, success, arguments_json,
            result_json, started_at, finished_at, error_code, error_message,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tool_call_id,
            task_id,
            tool_name,
            source,
            int(success),
            _json(arguments or {}),
            _json(result or {}),
            started_at,
            finished_at,
            error_code,
            error_message,
            _now(),
        ),
    )
    connection.commit()


def insert_run_report(
    connection: sqlite3.Connection,
    *,
    report_id: str,
    task_id: str | None,
    source: str,
    status: str,
    run_report_path: str | None,
    report: dict[str, Any],
    _commit: bool = True,
) -> None:
    """Insert or update one run report summary."""

    connection.execute(
        """
        INSERT OR REPLACE INTO run_reports (
            report_id, task_id, source, status, run_report_path, report_json,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id,
            task_id,
            source,
            status,
            run_report_path,
            _json(report),
            _now(),
        ),
    )
    if _commit:
        connection.commit()


def fetch_one(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    """Fetch one row as a plain dictionary for tests and simple callers."""

    row = connection.execute(query, parameters).fetchone()
    return dict(row) if row is not None else None


def fetch_all(
    connection: sqlite3.Connection,
    query: str,
    parameters: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """Fetch rows as plain dictionaries for tests and simple callers."""

    return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def _json(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    return value


def _optional_bool(value: Any) -> int | None:
    if value is None:
        return None
    return int(bool(value))


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        value = str(value)
    cleaned = value.strip()
    return cleaned or None


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _execute_schema_script(connection: sqlite3.Connection, script: str) -> None:
    """Execute a static SQL script without sqlite3.executescript auto-commits."""

    pending = ""
    for line in script.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            statement = pending.strip()
            if statement:
                connection.execute(statement)
            pending = ""
    if pending.strip():
        raise sqlite3.OperationalError("incomplete schema SQL statement")


def _backfill_discovery_history(connection: sqlite3.Connection) -> None:
    """Best-effort backfill from legacy latest-task pointers."""

    connection.execute(
        """
        INSERT OR IGNORE INTO lead_discoveries (
            task_id, lead_id, source, discovered_at, discovery_status,
            source_record_id, metadata_json, created_at
        )
        SELECT
            task_id, lead_id, 'legacy', COALESCE(created_at, updated_at),
            'legacy_unknown', pmid, '{}', COALESCE(created_at, updated_at)
        FROM leads
        WHERE task_id IS NOT NULL
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO paper_discoveries (
            task_id, paper_id, source, discovered_at, source_record_id,
            metadata_json, created_at
        )
        SELECT
            task_id, paper_id, 'legacy', COALESCE(created_at, updated_at),
            pmid, '{}', COALESCE(created_at, updated_at)
        FROM papers
        WHERE task_id IS NOT NULL
        """
    )


def _validate_discovery_history(connection: sqlite3.Connection) -> None:
    """Ensure every recoverable legacy task pointer has a discovery row."""

    missing_leads = connection.execute(
        """
        SELECT COUNT(*)
        FROM leads AS l
        LEFT JOIN lead_discoveries AS d
            ON d.task_id = l.task_id AND d.lead_id = l.lead_id
        WHERE l.task_id IS NOT NULL AND d.lead_id IS NULL
        """
    ).fetchone()[0]
    missing_papers = connection.execute(
        """
        SELECT COUNT(*)
        FROM papers AS p
        LEFT JOIN paper_discoveries AS d
            ON d.task_id = p.task_id AND d.paper_id = p.paper_id
        WHERE p.task_id IS NOT NULL AND d.paper_id IS NULL
        """
    ).fetchone()[0]
    if missing_leads or missing_papers:
        raise RuntimeError("discovery history backfill validation failed")


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id TEXT PRIMARY KEY,
    title TEXT,
    status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_created
ON conversation_messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS conversation_state (
    conversation_id TEXT PRIMARY KEY,
    task_id TEXT,
    last_run_report_path TEXT,
    last_lead_ids_json TEXT NOT NULL DEFAULT '[]',
    last_selected_lead_ids_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    query TEXT,
    status TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    run_report_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    task_id TEXT,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    pmid TEXT,
    doi TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    journal TEXT,
    publisher TEXT,
    publication_date TEXT,
    publication_year INTEGER,
    authors_json TEXT NOT NULL,
    organizations_json TEXT NOT NULL,
    source_url TEXT,
    raw_record_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS researchers (
    researcher_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    emails_json TEXT NOT NULL DEFAULT '[]',
    organizations_json TEXT NOT NULL DEFAULT '[]',
    country TEXT,
    merge_status TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    contact_id TEXT PRIMARY KEY,
    researcher_id TEXT,
    contact_type TEXT NOT NULL,
    value TEXT,
    status TEXT NOT NULL,
    source_url TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(researcher_id) REFERENCES researchers(researcher_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS funding_records (
    funding_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    grant_id TEXT,
    agency TEXT,
    project_title TEXT,
    pi_name TEXT,
    institution TEXT,
    fiscal_year INTEGER,
    amount REAL,
    source_url TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    task_id TEXT,
    pi_full_name TEXT NOT NULL,
    verified_email TEXT,
    email_status TEXT,
    institution TEXT,
    country TEXT,
    priority TEXT,
    lead_score INTEGER,
    pmid TEXT,
    doi TEXT,
    data_quality TEXT,
    manual_review_required INTEGER NOT NULL DEFAULT 1,
    raw_affiliation TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS lead_discoveries (
    task_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    source TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    discovery_status TEXT NOT NULL DEFAULT 'legacy_unknown',
    source_record_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    PRIMARY KEY(task_id, lead_id),
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY(lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lead_discoveries_lead_id
ON lead_discoveries(lead_id);

CREATE INDEX IF NOT EXISTS idx_lead_discoveries_task_id
ON lead_discoveries(task_id);

CREATE INDEX IF NOT EXISTS idx_lead_discoveries_discovered_at
ON lead_discoveries(discovered_at);

CREATE TABLE IF NOT EXISTS paper_discoveries (
    task_id TEXT NOT NULL,
    paper_id TEXT NOT NULL,
    source TEXT NOT NULL,
    discovered_at TEXT NOT NULL,
    source_record_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    PRIMARY KEY(task_id, paper_id),
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
    FOREIGN KEY(paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_paper_discoveries_paper_id
ON paper_discoveries(paper_id);

CREATE INDEX IF NOT EXISTS idx_paper_discoveries_task_id
ON paper_discoveries(task_id);

CREATE INDEX IF NOT EXISTS idx_paper_discoveries_discovered_at
ON paper_discoveries(discovered_at);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_url TEXT,
    retrieved_at TEXT,
    field_name TEXT NOT NULL,
    field_value TEXT,
    confidence TEXT,
    raw_record_path TEXT,
    note TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_drafts (
    draft_id TEXT PRIMARY KEY,
    lead_id TEXT,
    recipient_name TEXT,
    verified_email TEXT,
    subject TEXT,
    body TEXT,
    language TEXT,
    draft_status TEXT,
    human_reviewer TEXT,
    reviewed_at TEXT,
    can_send INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(lead_id) REFERENCES leads(lead_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS email_reviews (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    lead_id TEXT,
    actor TEXT,
    occurred_at TEXT,
    status_before TEXT,
    status_after TEXT,
    permission_allowed INTEGER,
    permission_blockers_json TEXT NOT NULL DEFAULT '[]',
    note TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS email_send_logs (
    send_id TEXT PRIMARY KEY,
    draft_id TEXT,
    lead_id TEXT,
    recipient_email TEXT,
    provider TEXT,
    status TEXT NOT NULL,
    provider_message_id TEXT,
    attempted_at TEXT,
    finished_at TEXT,
    actor TEXT,
    permission_allowed INTEGER,
    permission_blockers_json TEXT NOT NULL DEFAULT '[]',
    permission_warnings_json TEXT NOT NULL DEFAULT '[]',
    error_type TEXT,
    error_message TEXT,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(draft_id) REFERENCES email_drafts(draft_id) ON DELETE SET NULL,
    FOREIGN KEY(lead_id) REFERENCES leads(lead_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ai_usage (
    usage_id TEXT PRIMARY KEY,
    account_alias TEXT,
    provider TEXT,
    called_at TEXT,
    feature_module TEXT,
    model_name TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    estimated_cost REAL,
    currency TEXT,
    pricing_config_version TEXT,
    status TEXT,
    error_type TEXT,
    error_message TEXT,
    task_id TEXT,
    lead_id TEXT,
    started_at TEXT,
    finished_at TEXT,
    latency_ms INTEGER
);

CREATE TABLE IF NOT EXISTS tool_calls (
    tool_call_id TEXT PRIMARY KEY,
    task_id TEXT,
    tool_name TEXT NOT NULL,
    source TEXT,
    success INTEGER NOT NULL,
    arguments_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS run_reports (
    report_id TEXT PRIMARY KEY,
    task_id TEXT,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    run_report_path TEXT,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    task_id TEXT,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    total_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    blocked_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    last_error TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_task_status
ON jobs(task_id, status);

CREATE TABLE IF NOT EXISTS job_items (
    job_item_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    lead_id TEXT,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_job_items_job_status
ON job_items(job_id, status);

CREATE TABLE IF NOT EXISTS agent_run_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL,
    response_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""
