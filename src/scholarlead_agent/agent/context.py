"""Context builder for minimal multi-turn Agent runs."""

from __future__ import annotations

import json
from typing import Any

from scholarlead_agent.agent.conversation import (
    ConversationMessage,
    TaskContext,
    utc_now_iso,
)
from scholarlead_agent.agent.messages import assistant_message, system_message, user_message


DEFAULT_RECENT_MESSAGE_LIMIT = 8


def build_task_context_summary(context: TaskContext | None) -> str:
    """Build a compact task context summary for the model."""

    if context is None:
        return "No previous task context is available."

    lines = [
        "Current task context:",
        f"- conversation_id: {context.conversation_id}",
        f"- task_id: {context.task_id or 'unknown'}",
        f"- last_run_report_path: {context.last_run_report_path or 'unknown'}",
        f"- last_lead_ids: {_join_ids(context.last_lead_ids)}",
        f"- last_selected_lead_ids: {_join_ids(context.last_selected_lead_ids)}",
    ]
    return "\n".join(lines)


def build_context_messages(
    *,
    task_context: TaskContext | None = None,
    recent_messages: list[ConversationMessage] | None = None,
    limit: int = DEFAULT_RECENT_MESSAGE_LIMIT,
) -> list[dict[str, Any]]:
    """Build bounded context messages before the current user message."""

    messages = [system_message(build_task_context_summary(task_context))]
    for message in (recent_messages or [])[-max(0, limit) :]:
        converted = _conversation_message_to_model_message(message)
        if converted is not None:
            messages.append(converted)
    return messages


def task_context_from_agent_messages(
    *,
    conversation_id: str,
    messages: list[dict[str, Any]],
    previous: TaskContext | None = None,
) -> TaskContext:
    """Extract minimal task context from Agent tool messages."""

    task_id = previous.task_id if previous else None
    run_report_path = previous.last_run_report_path if previous else None
    lead_ids = list(previous.last_lead_ids) if previous else []

    for payload in _iter_tool_payloads(messages):
        data = payload.get("data")
        if not isinstance(data, dict):
            continue
        task_id = _first_string(data.get("task_id"), task_id)
        run_report_path = _first_string(data.get("run_report_path"), run_report_path)
        for lead_id in _lead_ids_from_payload(data):
            if lead_id not in lead_ids:
                lead_ids.append(lead_id)

    return TaskContext(
        conversation_id=conversation_id,
        task_id=task_id,
        last_run_report_path=run_report_path,
        last_lead_ids=lead_ids,
        last_selected_lead_ids=previous.last_selected_lead_ids if previous else [],
        updated_at=utc_now_iso(),
    )


def _conversation_message_to_model_message(
    message: ConversationMessage,
) -> dict[str, Any] | None:
    role = message.role
    if role == "user":
        return user_message(message.content)
    if role == "assistant":
        return assistant_message(content=message.content)
    if role == "system":
        return system_message(message.content)
    return None


def _join_ids(values: list[str]) -> str:
    cleaned = [value for value in values if value]
    return ", ".join(cleaned) if cleaned else "none"


def _iter_tool_payloads(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _lead_ids_from_payload(data: dict[str, Any]) -> list[str]:
    leads = data.get("leads")
    if not isinstance(leads, list):
        return []
    ids: list[str] = []
    for lead in leads:
        if not isinstance(lead, dict):
            continue
        lead_id = lead.get("lead_id")
        if isinstance(lead_id, str) and lead_id and lead_id not in ids:
            ids.append(lead_id)
    return ids


def _first_string(value: Any, fallback: str | None) -> str | None:
    if isinstance(value, str) and value:
        return value
    return fallback
