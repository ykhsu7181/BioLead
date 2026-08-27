import json
from typing import Any

import pytest

from scholarlead_agent.agent.loop import (
    AgentLimitError,
    AgentRunError,
    AgentRunner,
    IncompleteModelReplyError,
)
from scholarlead_agent.agent.model import ModelReply
from scholarlead_agent.agent.registry import ToolRegistry
from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult


class FakeModel:
    def __init__(self, replies: list[ModelReply] | None = None, error: Exception | None = None) -> None:
        self.replies = replies or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        if self.error is not None:
            raise self.error
        if not self.replies:
            return ModelReply(content="Done.")
        return self.replies.pop(0)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="lookup",
            description="Lookup test tool.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["query"],
                "properties": {"query": {"type": "string", "minLength": 1}},
            },
            effect="external",
            handler=lambda arguments: ToolResult(
                success=True,
                source="lookup",
                data={"query": arguments["query"], "answer": "tool data"},
            ),
        )
    )
    return registry


def tool_call(call_id: str, name: str = "lookup", arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments or {"query": "crispr"}),
        },
    }


def test_agent_loop_returns_direct_model_answer_without_tool() -> None:
    model = FakeModel([ModelReply(content="Direct answer.")])
    runner = AgentRunner(model=model, tool_registry=make_registry())

    result = runner.run("hello")

    assert result.final_answer == "Direct answer."
    assert result.turns == 1
    assert result.messages[-1] == {"role": "assistant", "content": "Direct answer."}
    assert model.calls[0]["tools"][0]["function"]["name"] == "lookup"


def test_agent_loop_invokes_tool_then_returns_final_answer() -> None:
    model = FakeModel(
        [
            ModelReply(tool_calls=[tool_call("call-1")], finish_reason="tool_calls"),
            ModelReply(content="I found tool data."),
        ]
    )
    runner = AgentRunner(model=model, tool_registry=make_registry())

    result = runner.run("find papers")

    assert result.final_answer == "I found tool data."
    assert result.turns == 2
    tool_messages = [message for message in result.messages if message["role"] == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call-1"
    assert tool_messages[0]["name"] == "lookup"
    payload = json.loads(tool_messages[0]["content"])
    assert payload["success"] is True
    assert payload["data"]["answer"] == "tool data"
    assert model.calls[1]["messages"][-1]["tool_call_id"] == "call-1"


def test_agent_loop_returns_tool_error_to_model_and_continues() -> None:
    model = FakeModel(
        [
            ModelReply(tool_calls=[tool_call("bad-1", name="missing")], finish_reason="tool_calls"),
            ModelReply(content="The tool was not available."),
        ]
    )
    runner = AgentRunner(model=model, tool_registry=make_registry())

    result = runner.run("use missing tool")

    tool_message = [message for message in result.messages if message["role"] == "tool"][0]
    payload = json.loads(tool_message["content"])
    assert tool_message["tool_call_id"] == "bad-1"
    assert payload["success"] is False
    assert payload["error_code"] == "unknown_tool"
    assert result.final_answer == "The tool was not available."


def test_agent_loop_pairs_multiple_tool_call_ids() -> None:
    model = FakeModel(
        [
            ModelReply(
                tool_calls=[
                    tool_call("call-a", arguments={"query": "a"}),
                    tool_call("call-b", arguments={"query": "b"}),
                ],
                finish_reason="tool_calls",
            ),
            ModelReply(content="Both tools returned."),
        ]
    )
    runner = AgentRunner(model=model, tool_registry=make_registry())

    result = runner.run("run two tools")

    tool_messages = [message for message in result.messages if message["role"] == "tool"]
    assert [message["tool_call_id"] for message in tool_messages] == ["call-a", "call-b"]
    assert [json.loads(message["content"])["data"]["query"] for message in tool_messages] == ["a", "b"]


def test_agent_loop_raises_on_max_turns() -> None:
    model = FakeModel(
        [
            ModelReply(tool_calls=[tool_call("call-1")], finish_reason="tool_calls"),
            ModelReply(tool_calls=[tool_call("call-2")], finish_reason="tool_calls"),
        ]
    )
    runner = AgentRunner(model=model, tool_registry=make_registry(), max_turns=1)

    with pytest.raises(AgentLimitError, match="max_turns=1"):
        runner.run("keep going")


def test_agent_loop_rejects_empty_final_reply() -> None:
    model = FakeModel([ModelReply(content="")])
    runner = AgentRunner(model=model, tool_registry=make_registry())

    with pytest.raises(IncompleteModelReplyError, match="no final content"):
        runner.run("hello")


def test_agent_loop_rejects_truncated_or_filtered_reply() -> None:
    for finish_reason in ["length", "content_filter"]:
        model = FakeModel([ModelReply(content="partial", finish_reason=finish_reason)])
        runner = AgentRunner(model=model, tool_registry=make_registry())

        with pytest.raises(IncompleteModelReplyError, match=finish_reason):
            runner.run("hello")


def test_agent_loop_converts_model_exception() -> None:
    model = FakeModel(error=RuntimeError("model down"))
    runner = AgentRunner(model=model, tool_registry=make_registry())

    with pytest.raises(AgentRunError, match="model call failed"):
        runner.run("hello")


def test_agent_loop_requires_tool_call_id() -> None:
    call = tool_call("call-1")
    del call["id"]
    model = FakeModel([ModelReply(tool_calls=[call], finish_reason="tool_calls")])
    runner = AgentRunner(model=model, tool_registry=make_registry())

    with pytest.raises(IncompleteModelReplyError, match="tool_call id is required"):
        runner.run("hello")


def test_agent_loop_source_has_no_specific_tool_branch() -> None:
    from pathlib import Path

    source = Path("src/scholarlead_agent/agent/loop.py").read_text(encoding="utf-8")

    assert "if tool_name ==" not in source
