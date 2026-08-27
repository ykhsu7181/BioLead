"""Default Agent runtime assembly for ScholarLead Agent."""

from __future__ import annotations

import json
from typing import Any

from scholarlead_agent.adapters.openai_compatible_chat import OpenAICompatibleChatAdapter
from scholarlead_agent.agent.context import (
    build_context_messages,
    task_context_from_agent_messages,
)
from scholarlead_agent.agent.conversation import (
    ConversationMessage,
    TaskContext,
    new_conversation_id,
    new_message_id,
    utc_now_iso,
)
from scholarlead_agent.agent.loop import AgentRunResult, AgentRunner
from scholarlead_agent.agent.model import ModelClient
from scholarlead_agent.agent.registry import ToolContext, ToolRegistry
from scholarlead_agent.ai.model_config import FEATURE_AGENT_REASONING
from scholarlead_agent.ai.usage import UsageTrackingModelClient
from scholarlead_agent.config import load_config
from scholarlead_agent.database import (
    fetch_conversation_messages,
    fetch_task_context,
    initialize_database,
    insert_conversation,
    insert_conversation_message,
    upsert_conversation_state,
)
from scholarlead_agent.tools.crossref_tool import SEARCH_CROSSREF_TOOL
from scholarlead_agent.tools.email_draft_tool import GENERATE_EMAIL_DRAFT_TOOL
from scholarlead_agent.tools.funding_tool import SEARCH_FUNDING_TOOL
from scholarlead_agent.tools.openalex_tool import SEARCH_OPENALEX_TOOL
from scholarlead_agent.tools.pubmed_tool import SEARCH_PUBMED_TOOL


def build_default_tool_registry() -> ToolRegistry:
    """Build the default business ToolRegistry."""

    registry = ToolRegistry()
    registry.register(SEARCH_PUBMED_TOOL)
    registry.register(SEARCH_CROSSREF_TOOL)
    registry.register(SEARCH_OPENALEX_TOOL)
    registry.register(SEARCH_FUNDING_TOOL)
    registry.register(GENERATE_EMAIL_DRAFT_TOOL)
    return registry


def build_default_model_client() -> ModelClient:
    """Build the configured model client."""

    config = load_config()
    adapter = OpenAICompatibleChatAdapter(
        config=config,
        feature_module=FEATURE_AGENT_REASONING,
    )
    return UsageTrackingModelClient(
        inner=adapter,
        feature_module=FEATURE_AGENT_REASONING,
        config=config,
    )


def run_agent_task(
    user_input: str,
    *,
    model: ModelClient | None = None,
    tool_registry: ToolRegistry | None = None,
    max_turns: int = 6,
    context: ToolContext | None = None,
    task_context: TaskContext | None = None,
    recent_messages: list[ConversationMessage] | None = None,
) -> AgentRunResult:
    """Run one natural-language Agent task."""

    runner = AgentRunner(
        model=model or build_default_model_client(),
        tool_registry=tool_registry or build_default_tool_registry(),
        max_turns=max_turns,
        context=context,
    )
    context_messages = (
        build_context_messages(
            task_context=task_context,
            recent_messages=recent_messages,
        )
        if task_context is not None or recent_messages
        else None
    )
    return runner.run_with_context(user_input, context_messages=context_messages)


def run_agent_conversation(
    user_input: str,
    *,
    conversation_id: str | None = None,
    model: ModelClient | None = None,
    tool_registry: ToolRegistry | None = None,
    max_turns: int = 6,
    context: ToolContext | None = None,
    database_path: str | None = None,
) -> tuple[str, AgentRunResult, TaskContext]:
    """Run an Agent turn and persist minimal conversation context."""

    config = load_config()
    resolved_conversation_id = conversation_id or new_conversation_id()
    db_path = database_path or str(config.database_path)

    with initialize_database(db_path) as connection:
        insert_conversation(
            connection,
            conversation_id=resolved_conversation_id,
            title=user_input[:80],
            status="active",
        )
        previous_context = fetch_task_context(connection, resolved_conversation_id)
        recent_messages = fetch_conversation_messages(
            connection,
            resolved_conversation_id,
            limit=8,
        )
        insert_conversation_message(
            connection,
            ConversationMessage(
                message_id=new_message_id(),
                conversation_id=resolved_conversation_id,
                role="user",
                content=user_input,
                created_at=utc_now_iso(),
            ),
        )

    result = run_agent_task(
        user_input,
        model=model,
        tool_registry=tool_registry,
        max_turns=max_turns,
        context=context,
        task_context=previous_context,
        recent_messages=recent_messages,
    )
    updated_context = task_context_from_agent_messages(
        conversation_id=resolved_conversation_id,
        messages=result.messages,
        previous=previous_context,
    )

    with initialize_database(db_path) as connection:
        insert_conversation_message(
            connection,
            ConversationMessage(
                message_id=new_message_id(),
                conversation_id=resolved_conversation_id,
                role="assistant",
                content=result.final_answer,
                created_at=utc_now_iso(),
            ),
        )
        upsert_conversation_state(connection, updated_context)

    return resolved_conversation_id, result, updated_context


def extract_tool_names(messages: list[dict[str, Any]]) -> list[str]:
    """Return tool names invoked during an Agent run."""

    names: list[str] = []
    for message in messages:
        if message.get("role") != "tool":
            continue
        name = message.get("name")
        if isinstance(name, str) and name not in names:
            names.append(name)
    return names


def extract_tool_sources(messages: list[dict[str, Any]]) -> list[str]:
    """Return data source names reported by tool results."""

    sources: list[str] = []
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
        for source in _tool_sources_from_payload(payload):
            if source not in sources:
                sources.append(source)
    return sources


def extract_run_report_paths(messages: list[dict[str, Any]]) -> list[str]:
    """Return run report paths from PubMed tool results, if present."""

    paths: list[str] = []
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
        path = _nested_string(payload, ["data", "run_report_path"])
        if path and path not in paths:
            paths.append(path)
    return paths


def _tool_sources_from_payload(payload: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    for value in [
        payload.get("source"),
        _nested_string(payload, ["data", "source"]),
    ]:
        if isinstance(value, str) and value and value not in sources:
            sources.append(value)
    queried_sources = payload.get("data", {}).get("queried_sources")
    if isinstance(queried_sources, list):
        for source in queried_sources:
            if isinstance(source, str) and source and source not in sources:
                sources.append(source)
    return sources


def _nested_string(payload: dict[str, Any], path: list[str]) -> str | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, str) and value else None
