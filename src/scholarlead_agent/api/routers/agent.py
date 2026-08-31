"""Natural-language Agent execution API route."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from fastapi import APIRouter, Depends

from scholarlead_agent.adapters.openai_compatible_chat import LLMConfigError
from scholarlead_agent.agent.loop import AgentLimitError, AgentRunError
from scholarlead_agent.agent.conversation import with_selected_lead_ids
from scholarlead_agent.agent.registry import ToolContext
from scholarlead_agent.agent.runtime import (
    extract_tool_names,
    extract_tool_sources,
    run_agent_conversation,
)
from scholarlead_agent.api.dependencies import get_database
from scholarlead_agent.api.errors import ApiError, api_success
from scholarlead_agent.api.schemas.agent import AgentRunRequest
from scholarlead_agent.config import load_config
from scholarlead_agent.database import (
    claim_agent_run_idempotency,
    complete_agent_run_idempotency,
    fail_agent_run_idempotency,
    insert_conversation,
    upsert_conversation_state,
)
from scholarlead_agent.services.agent_lead_selection import select_agent_leads
from scholarlead_agent.services.agent_result_persistence import persist_agent_run_result


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/run")
def run_agent(
    request: AgentRunRequest,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    """Run one bounded Agent turn and persist supported Tool results."""

    message, conversation_id, max_turns, idempotency_key = _validate_request(request)
    fingerprint = _request_fingerprint(
        message=message,
        conversation_id=conversation_id,
        max_turns=max_turns,
    )
    if idempotency_key:
        prior = claim_agent_run_idempotency(
            connection,
            idempotency_key=idempotency_key,
            request_fingerprint=fingerprint,
        )
        if prior["state"] == "conflict":
            raise ApiError(
                "IDEMPOTENCY_KEY_CONFLICT",
                "idempotency_key was already used for a different request.",
                409,
            )
        if prior["state"] == "in_progress":
            raise ApiError("AGENT_RUN_IN_PROGRESS", "Agent run is already in progress.", 409)
        if prior["state"] == "completed":
            return api_success(prior["response"])

    try:
        config = load_config()
        resolved_conversation_id, result, task_context = run_agent_conversation(
            message,
            conversation_id=conversation_id,
            max_turns=max_turns,
            database_path=str(config.database_path),
            context=ToolContext(max_results_limit=config.agent_max_results_limit),
        )
    except LLMConfigError as error:
        _mark_failed(connection, idempotency_key)
        raise ApiError("MODEL_NOT_CONFIGURED", "Agent model is not configured.", 400) from error
    except AgentLimitError as error:
        _mark_failed(connection, idempotency_key)
        raise ApiError("AGENT_MAX_TURNS_EXCEEDED", "Agent reached its maximum turns.", 422) from error
    except AgentRunError as error:
        _mark_failed(connection, idempotency_key)
        raise ApiError("AGENT_RUN_FAILED", "Agent run failed.", 502) from error
    except Exception as error:
        _mark_failed(connection, idempotency_key)
        raise ApiError("AGENT_RUN_FAILED", "Agent run failed.", 500) from error

    try:
        persisted = persist_agent_run_result(connection, result)
    except Exception as error:
        _mark_failed(connection, idempotency_key)
        raise ApiError(
            "AGENT_RESULT_PERSISTENCE_FAILED",
            "Agent result could not be persisted.",
            500,
        ) from error

    selection = select_agent_leads(
        connection,
        message=message,
        current_turn_lead_ids=persisted.current_turn_lead_ids,
        task_context=task_context,
    )
    task_context = with_selected_lead_ids(task_context, selection.selected_lead_ids)
    insert_conversation(
        connection,
        conversation_id=task_context.conversation_id,
        title=message[:80],
        status="active",
    )
    upsert_conversation_state(connection, task_context)

    data = {
        "conversation_id": resolved_conversation_id,
        "status": "completed",
        "final_answer": result.final_answer,
        "turns": result.turns,
        "primary_task_id": persisted.primary_task_id,
        "task_ids_by_source": persisted.task_ids_by_source,
        "current_turn_lead_ids": persisted.current_turn_lead_ids,
        "context_lead_ids": list(task_context.last_lead_ids),
        "selected_lead_ids": selection.selected_lead_ids,
        "lead_selection_mode": selection.selection_mode,
        "tools_used": extract_tool_names(result.messages),
        "sources_used": extract_tool_sources(result.messages),
        "artifacts": persisted.artifacts,
        "result_summary": {
            "lead_count": persisted.reported_lead_count,
            "persisted_lead_count": persisted.persisted_lead_count,
            "selected_lead_count": len(selection.selected_lead_ids),
        },
    }
    if idempotency_key:
        complete_agent_run_idempotency(
            connection,
            idempotency_key=idempotency_key,
            response=data,
        )
    return api_success(data)


def _validate_request(request: AgentRunRequest) -> tuple[str, str | None, int, str | None]:
    message = _required_text(request.message, "message", maximum=2000)
    conversation_id = _optional_text(request.conversation_id, "conversation_id", maximum=200)
    idempotency_key = _optional_text(request.idempotency_key, "idempotency_key", maximum=200)
    max_turns = request.max_turns
    if isinstance(max_turns, bool) or not isinstance(max_turns, int):
        raise ApiError("INVALID_AGENT_REQUEST", "max_turns must be an integer.", 400)
    if max_turns < 1 or max_turns > 6:
        raise ApiError("INVALID_AGENT_REQUEST", "max_turns must be between 1 and 6.", 400)
    return message, conversation_id, max_turns, idempotency_key


def _required_text(value: str | None, field_name: str, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ApiError("INVALID_AGENT_REQUEST", f"{field_name} is required.", 400)
    normalized = value.strip()
    if not normalized:
        raise ApiError("INVALID_AGENT_REQUEST", f"{field_name} cannot be empty.", 400)
    if len(normalized) > maximum:
        raise ApiError(
            "INVALID_AGENT_REQUEST",
            f"{field_name} must be at most {maximum} characters.",
            400,
        )
    return normalized


def _optional_text(
    value: str | None,
    field_name: str,
    *,
    maximum: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ApiError("INVALID_AGENT_REQUEST", f"{field_name} must be a string.", 400)
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ApiError("INVALID_AGENT_REQUEST", f"{field_name} is invalid.", 400)
    return normalized


def _request_fingerprint(
    *,
    message: str,
    conversation_id: str | None,
    max_turns: int,
) -> str:
    payload = json.dumps(
        {
            "message": message,
            "conversation_id": conversation_id,
            "max_turns": max_turns,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mark_failed(connection: sqlite3.Connection, idempotency_key: str | None) -> None:
    if idempotency_key:
        fail_agent_run_idempotency(connection, idempotency_key=idempotency_key)
