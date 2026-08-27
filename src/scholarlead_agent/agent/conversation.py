"""Minimal conversation state for Agent task continuity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


CONVERSATION_SCHEMA_VERSION = "conversation-v1"


@dataclass(frozen=True)
class ConversationMessage:
    """One persisted conversation message."""

    message_id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskContext:
    """Small task state used to resolve follow-up references."""

    conversation_id: str
    task_id: str | None = None
    last_run_report_path: str | None = None
    last_lead_ids: list[str] = field(default_factory=list)
    last_selected_lead_ids: list[str] = field(default_factory=list)
    updated_at: str = ""


def new_conversation_id() -> str:
    """Return a stable opaque conversation id."""

    return f"conv-{uuid4()}"


def new_message_id() -> str:
    """Return a stable opaque message id."""

    return f"msg-{uuid4()}"


def utc_now_iso() -> str:
    """Return a second-precision UTC timestamp string."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def conversation_message_to_dict(message: ConversationMessage) -> dict[str, Any]:
    """Convert a conversation message to a JSON-friendly dict."""

    return {
        "message_id": message.message_id,
        "conversation_id": message.conversation_id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at,
        "metadata": dict(message.metadata),
    }


def task_context_to_dict(context: TaskContext) -> dict[str, Any]:
    """Convert task context to a JSON-friendly dict."""

    return {
        "conversation_id": context.conversation_id,
        "task_id": context.task_id,
        "last_run_report_path": context.last_run_report_path,
        "last_lead_ids": list(context.last_lead_ids),
        "last_selected_lead_ids": list(context.last_selected_lead_ids),
        "updated_at": context.updated_at,
    }
