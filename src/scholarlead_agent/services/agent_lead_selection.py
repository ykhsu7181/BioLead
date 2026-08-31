"""Deterministic Lead selection for bounded Agent follow-up requests."""

from __future__ import annotations

from dataclasses import dataclass
import re
import sqlite3

from scholarlead_agent.agent.conversation import TaskContext


@dataclass(frozen=True)
class AgentLeadSelection:
    """Structured Lead IDs selected for one Agent response."""

    selected_lead_ids: list[str]
    selection_mode: str


def select_agent_leads(
    connection: sqlite3.Connection,
    *,
    message: str,
    current_turn_lead_ids: list[str],
    task_context: TaskContext,
) -> AgentLeadSelection:
    """Select current or contextual Leads using explicit deterministic intent."""

    candidate_ids = _unique_ids(current_turn_lead_ids)
    if candidate_ids:
        selection_mode = "current_turn"
    else:
        candidate_ids = _unique_ids(
            task_context.last_selected_lead_ids or task_context.last_lead_ids
        )
        selection_mode = "conversation_context"

    if _requests_verified_email_only(message):
        return AgentLeadSelection(
            selected_lead_ids=_verified_email_lead_ids(connection, candidate_ids),
            selection_mode="verified_email_only",
        )
    return AgentLeadSelection(
        selected_lead_ids=candidate_ids,
        selection_mode=selection_mode,
    )


def _requests_verified_email_only(message: str) -> bool:
    normalized = " ".join(message.lower().split())
    chinese_patterns = (
        r"(?:只|仅|只要).{0,20}(?:验证|公开).{0,12}邮箱",
        r"保留.{0,20}(?:验证|公开).{0,12}邮箱",
    )
    english_pattern = r"\b(?:only keep|keep only|retain only)\b.*\b(?:verified|public)\b.*\bemail"
    return any(re.search(pattern, normalized) for pattern in chinese_patterns) or bool(
        re.search(english_pattern, normalized)
    )


def _verified_email_lead_ids(
    connection: sqlite3.Connection,
    candidate_ids: list[str],
) -> list[str]:
    if not candidate_ids:
        return []
    placeholders = ", ".join("?" for _ in candidate_ids)
    rows = connection.execute(
        f"""
        SELECT lead_id
        FROM leads
        WHERE lead_id IN ({placeholders})
          AND verified_email IS NOT NULL
          AND TRIM(verified_email) <> ''
          AND LOWER(TRIM(verified_email)) NOT IN ('missing', 'unknown')
          AND email_status LIKE 'verified_%'
        """,
        candidate_ids,
    ).fetchall()
    verified_ids = {str(row["lead_id"]) for row in rows}
    return [lead_id for lead_id in candidate_ids if lead_id in verified_ids]


def _unique_ids(values: list[str]) -> list[str]:
    results: list[str] = []
    for value in values:
        if isinstance(value, str) and value and value not in results:
            results.append(value)
    return results
