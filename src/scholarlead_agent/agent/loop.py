"""Formal bounded Agent Loop for ScholarLead Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scholarlead_agent.agent.messages import (
    assistant_message,
    system_message,
    tool_message,
    user_message,
)
from scholarlead_agent.agent.model import ModelClient, ModelReply
from scholarlead_agent.agent.registry import ToolContext, ToolRegistry
from scholarlead_agent.agent.tool_types import ToolResult


DEFAULT_SYSTEM_PROMPT = """You are ScholarLead Agent.

You help users discover overseas scientific customer leads from evidence-backed
literature data. Use available tools when the user needs real literature,
authors, public email evidence, PubMed leads, or temporary PubMed-only scoring.
Available data-source tools include search_pubmed, search_crossref,
search_openalex, and search_funding.
Use search_pubmed as the main lead-discovery path when the user asks for papers,
candidate PIs, public email evidence, PubMed leads, or PubMed-only lead exports.
Use Crossref only for DOI and publication metadata supplementation such as
title, journal, publisher, publication date, citation counts, and explicit
Crossref funder metadata. Do not treat Crossref as a primary email source or as
proof of active funding.
Use OpenAlex for open literature graph enrichment such as DOI completion,
abstracts, authorship, institutions, and publication metadata. Do not treat
OpenAlex results as verified emails, confirmed funding, or scored leads.
Use NIH RePORTER funding search only for explicit NIH project evidence. NIH
RePORTER does not cover all grants, so absence of NIH records is not proof of
no funding. Do not merge a PI or infer funding only because a paper author name
looks similar.
For multi-source tasks, call the needed tools through ToolRegistry and then
explain which sources were used. Do not hard-code assumptions about unavailable
tools, and do not hide tool failures.
When using tools, convert the user request into structured tool arguments:
query, from_date, to_date, max_results, country, and service_type for PubMed;
doi, title, and max_results for Crossref; query/date/max_results for OpenAlex;
and pi_name, institution, keyword, from_year, to_year, and max_results for
funding search.
Do not pass the whole natural-language request as every field. If query,
from_date, to_date, or max_results is missing, ask a concise follow-up question
instead of inventing values.
When the user asks for an email draft, generate only a human-review draft from
provided Lead and paper evidence. You may use generate_email_draft after a lead
has been selected or provided. Do not claim the candidate PI is fully confirmed.
Do not present PubMed-only temporary scoring as official four-dimension scoring.
Official scoring requires explicit evidence for each dimension and must clearly
mark missing funding or outsourcing evidence instead of guessing.
Do not fabricate emails, funding records, affiliations, or source links. If
required information is missing, say so or ask for clarification. The current
system cannot send real emails.
"""


class AgentRunError(RuntimeError):
    """Base error for Agent Loop failures."""


class AgentLimitError(AgentRunError):
    """Raised when the Agent Loop reaches its turn limit."""


class IncompleteModelReplyError(AgentRunError):
    """Raised when the model reply cannot be used to continue or finish."""


@dataclass(frozen=True)
class AgentRunResult:
    """Final Agent Loop output."""

    final_answer: str
    messages: list[dict[str, Any]]
    turns: int
    tool_executions: list["AgentToolExecution"] = field(default_factory=list)


@dataclass(frozen=True)
class AgentToolExecution:
    """One internal Tool result retained for post-run persistence."""

    name: str
    result: ToolResult


class AgentRunner:
    """Bounded Agent Loop that delegates all tool behavior to ToolRegistry."""

    def __init__(
        self,
        *,
        model: ModelClient,
        tool_registry: ToolRegistry,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_turns: int = 6,
        context: ToolContext | None = None,
    ) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        self.model = model
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.context = context or ToolContext()

    def run(self, user_input: str) -> AgentRunResult:
        """Run the Agent Loop for one user request."""

        return self.run_with_context(user_input, context_messages=None)

    def run_with_context(
        self,
        user_input: str,
        *,
        context_messages: list[dict[str, Any]] | None = None,
    ) -> AgentRunResult:
        """Run one request with optional bounded conversation context."""

        messages = [
            system_message(self.system_prompt),
            *(context_messages or []),
            user_message(user_input),
        ]
        tool_executions: list[AgentToolExecution] = []

        for turn_index in range(1, self.max_turns + 1):
            reply = self._complete(messages)
            self._raise_for_incomplete_reply(reply)

            tool_calls = reply.tool_calls or []
            if tool_calls:
                messages.append(
                    assistant_message(content=reply.content, tool_calls=tool_calls)
                )
                for tool_call in tool_calls:
                    tool_message_payload, execution = self._execute_tool_call(tool_call)
                    messages.append(tool_message_payload)
                    tool_executions.append(execution)
                continue

            if reply.content and reply.content.strip():
                messages.append(assistant_message(content=reply.content))
                return AgentRunResult(
                    final_answer=reply.content,
                    messages=messages,
                    turns=turn_index,
                    tool_executions=tool_executions,
                )

            raise IncompleteModelReplyError("model reply had no final content")

        raise AgentLimitError(f"agent reached max_turns={self.max_turns}")

    def _complete(self, messages: list[dict[str, Any]]) -> ModelReply:
        try:
            reply = self.model.complete(
                messages=messages,
                tools=self.tool_registry.to_model_tools(),
            )
        except Exception as error:
            raise AgentRunError(f"model call failed: {error}") from error

        if not isinstance(reply, ModelReply):
            raise IncompleteModelReplyError("model must return ModelReply")
        return reply

    def _execute_tool_call(
        self,
        tool_call: dict[str, Any],
    ) -> tuple[dict[str, Any], AgentToolExecution]:
        tool_call_id = _extract_tool_call_id(tool_call)
        tool_name = _extract_tool_name(tool_call)
        preparation = self.tool_registry.prepare(tool_call, context=self.context)

        if preparation.success and preparation.prepared_call is not None:
            result = self.tool_registry.invoke(
                preparation.prepared_call,
                context=self.context,
            )
            return (
                tool_message(
                    tool_call_id=tool_call_id,
                    name=preparation.prepared_call.name,
                    result=result,
                ),
                AgentToolExecution(name=preparation.prepared_call.name, result=result),
            )

        result = ToolResult(
            success=False,
            source="tool_registry",
            error_code=preparation.error_code or "tool_prepare_error",
            error_message=preparation.error_message,
            errors=preparation.errors,
        )
        name = tool_name or "unknown"
        return (
            tool_message(
                tool_call_id=tool_call_id,
                name=name,
                result=result,
            ),
            AgentToolExecution(name=name, result=result),
        )

    def _raise_for_incomplete_reply(self, reply: ModelReply) -> None:
        if reply.finish_reason in {"length", "content_filter"}:
            raise IncompleteModelReplyError(
                f"model reply incomplete: {reply.finish_reason}"
            )
        if reply.finish_reason not in {"stop", "tool_calls"}:
            raise IncompleteModelReplyError(
                f"unsupported model finish_reason: {reply.finish_reason}"
            )


def _extract_tool_call_id(tool_call: dict[str, Any]) -> str:
    value = tool_call.get("id") if isinstance(tool_call, dict) else None
    if isinstance(value, str) and value:
        return value
    raise IncompleteModelReplyError("tool_call id is required")


def _extract_tool_name(tool_call: dict[str, Any]) -> str | None:
    if not isinstance(tool_call, dict):
        return None
    function = tool_call.get("function")
    if isinstance(function, dict) and isinstance(function.get("name"), str):
        return function["name"]
    if isinstance(tool_call.get("name"), str):
        return tool_call["name"]
    return None
