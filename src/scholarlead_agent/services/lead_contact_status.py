"""Lead-level contact progress derived from draft and formal-send history."""

from __future__ import annotations

import sqlite3


CONTACT_STATUS_NOT_CONTACTED = "not_contacted"
CONTACT_STATUS_PENDING_REVIEW = "pending_review"
CONTACT_STATUS_READY_TO_SEND = "ready_to_send"
CONTACT_STATUS_SENT = "sent"
CONTACT_STATUS_REJECTED = "rejected"

CONTACT_STATUSES = (
    CONTACT_STATUS_NOT_CONTACTED,
    CONTACT_STATUS_PENDING_REVIEW,
    CONTACT_STATUS_READY_TO_SEND,
    CONTACT_STATUS_SENT,
    CONTACT_STATUS_REJECTED,
)

# Kept in one module so the list query and direct status lookup cannot drift.
LEAD_CONTACT_RANKS_CTE = """
lead_contact_ranks AS (
    SELECT
        d.lead_id,
        MAX(
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM email_send_logs AS s
                    WHERE s.draft_id = d.draft_id
                      AND LOWER(TRIM(COALESCE(s.status, ''))) = 'sent'
                      AND LOWER(TRIM(COALESCE(
                          CASE
                              WHEN json_valid(s.payload_json)
                              THEN json_extract(s.payload_json, '$.send_mode')
                          END,
                          ''
                      ))) = 'real_recipient'
                ) THEN 5
                WHEN LOWER(TRIM(COALESCE(d.draft_status, ''))) = 'review_approved'
                    THEN 4
                WHEN LOWER(TRIM(COALESCE(d.draft_status, ''))) IN (
                    'review_pending', 'changes_requested'
                ) THEN 3
                WHEN LOWER(TRIM(COALESCE(d.draft_status, ''))) = 'review_rejected'
                    THEN 2
                ELSE 3
            END
        ) AS contact_rank
    FROM email_drafts AS d
    WHERE d.lead_id IS NOT NULL
    GROUP BY d.lead_id
)
"""

LEAD_CONTACT_STATUS_SQL = """
CASE COALESCE(contact_ranks.contact_rank, 0)
    WHEN 5 THEN 'sent'
    WHEN 4 THEN 'ready_to_send'
    WHEN 3 THEN 'pending_review'
    WHEN 2 THEN 'rejected'
    ELSE 'not_contacted'
END
"""


def fetch_lead_contact_statuses(
    connection: sqlite3.Connection,
    lead_ids: list[str] | None = None,
) -> dict[str, str]:
    """Return deterministic contact progress for persisted Leads."""

    normalized_ids = list(dict.fromkeys(item for item in (lead_ids or []) if item))
    where_sql = ""
    parameters: list[str] = []
    if normalized_ids:
        placeholders = ", ".join("?" for _ in normalized_ids)
        where_sql = f"WHERE l.lead_id IN ({placeholders})"
        parameters.extend(normalized_ids)
    rows = connection.execute(
        f"""
        WITH {LEAD_CONTACT_RANKS_CTE}
        SELECT
            l.lead_id,
            {LEAD_CONTACT_STATUS_SQL} AS contact_status
        FROM leads AS l
        LEFT JOIN lead_contact_ranks AS contact_ranks
            ON contact_ranks.lead_id = l.lead_id
        {where_sql}
        """,
        tuple(parameters),
    ).fetchall()
    return {
        str(row["lead_id"]): str(row["contact_status"])
        for row in rows
    }
