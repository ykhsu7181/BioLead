import json

import pytest

from scholarlead_agent.agent.registry import ToolContext, ToolRegistry
from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult
from scholarlead_agent.tools.pubmed_tool import SEARCH_PUBMED_TOOL


def make_echo_tool(name: str = "echo") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description="Echo test tool.",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "required": ["message"],
            "properties": {
                "message": {"type": "string", "minLength": 1},
                "count": {"type": "integer", "minimum": 1, "maximum": 3},
            },
        },
        effect="read",
        handler=lambda arguments: ToolResult(
            success=True,
            source="echo",
            data={"arguments": arguments},
        ),
    )


def test_registry_registers_tool_and_returns_snapshot() -> None:
    registry = ToolRegistry()
    tool = make_echo_tool()

    registry.register(tool)
    snapshot = registry.snapshot()

    assert snapshot["echo"] is tool
    with pytest.raises(TypeError):
        snapshot["other"] = tool  # type: ignore[index]


def test_registry_rejects_duplicate_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    with pytest.raises(ValueError, match="tool already registered"):
        registry.register(make_echo_tool())


def test_registry_can_register_search_pubmed() -> None:
    registry = ToolRegistry()

    registry.register(SEARCH_PUBMED_TOOL)

    assert registry.snapshot()["search_pubmed"] is SEARCH_PUBMED_TOOL


def test_to_model_tools_hides_handler_and_keeps_schema() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    model_tools = registry.to_model_tools()

    assert model_tools == [
        {
            "type": "function",
            "function": {
                "name": "echo",
                "description": "Echo test tool.",
                "parameters": make_echo_tool().input_schema,
            },
        }
    ]
    assert "handler" not in json.dumps(model_tools)


def test_prepare_returns_unknown_tool_error() -> None:
    registry = ToolRegistry()

    result = registry.prepare(
        {"name": "missing", "arguments": json.dumps({"message": "hello"})}
    )

    assert result.success is False
    assert result.error_code == "unknown_tool"
    assert "unknown tool" in (result.error_message or "")


def test_prepare_rejects_invalid_json() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    result = registry.prepare({"name": "echo", "arguments": "{bad json"})

    assert result.success is False
    assert result.error_code == "invalid_tool_call"
    assert "valid JSON" in (result.error_message or "")


def test_prepare_rejects_non_object_arguments() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    result = registry.prepare({"name": "echo", "arguments": "[1, 2]"})

    assert result.success is False
    assert result.error_code == "invalid_tool_call"
    assert "arguments must be an object" in (result.error_message or "")


def test_prepare_rejects_schema_failure() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())

    result = registry.prepare(
        {"name": "echo", "arguments": json.dumps({"message": "", "count": 4})}
    )

    assert result.success is False
    assert result.error_code == "invalid_arguments"
    assert result.errors == [
        {"path": "message", "message": "message must have length at least 1"},
        {"path": "count", "message": "count must be <= 3"},
    ]


def test_prepare_validates_string_arrays() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="keywords",
            description="Keyword array test tool.",
            input_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["matched_keywords"],
                "properties": {
                    "matched_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
            },
            effect="read",
            handler=lambda arguments: ToolResult(
                success=True,
                source="keywords",
                data=arguments,
            ),
        )
    )

    accepted = registry.prepare(
        {
            "name": "keywords",
            "arguments": json.dumps({"matched_keywords": ["CRISPR", "RNA"]}),
        }
    )
    rejected = registry.prepare(
        {
            "name": "keywords",
            "arguments": json.dumps({"matched_keywords": ["CRISPR", 3]}),
        }
    )

    assert accepted.success is True
    assert rejected.success is False
    assert rejected.errors == [
        {
            "path": "matched_keywords.1",
            "message": "matched_keywords.1 must be a string",
        }
    ]


def test_prepare_accepts_openai_style_tool_call_and_context() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())
    context = ToolContext(workspace="D:/ScholarLead Agent", task_id="task-1")

    result = registry.prepare(
        {
            "function": {
                "name": "echo",
                "arguments": json.dumps({"message": "hello", "count": 2}),
            }
        },
        context=context,
    )

    assert result.success is True
    assert result.prepared_call is not None
    assert result.prepared_call.name == "echo"
    assert result.prepared_call.arguments == {"message": "hello", "count": 2}
    assert result.prepared_call.context is context


def test_invoke_runs_prepared_tool() -> None:
    registry = ToolRegistry()
    registry.register(make_echo_tool())
    prepared = registry.prepare(
        {"name": "echo", "arguments": json.dumps({"message": "hello"})}
    ).prepared_call

    assert prepared is not None
    result = registry.invoke(prepared)

    assert result.success is True
    assert result.source == "echo"
    assert result.data == {"arguments": {"message": "hello"}}


def test_invoke_converts_handler_exception() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="explode",
            description="Exploding test tool.",
            input_schema={"type": "object", "properties": {}},
            effect="read",
            handler=lambda arguments: (_ for _ in ()).throw(RuntimeError("boom")),
        )
    )
    prepared = registry.prepare({"name": "explode", "arguments": "{}"}).prepared_call

    assert prepared is not None
    result = registry.invoke(prepared)

    assert result.success is False
    assert result.error_code == "tool_execution_error"
    assert result.error_message == "boom"


def test_invoke_rejects_invalid_handler_result() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="bad",
            description="Bad result test tool.",
            input_schema={"type": "object", "properties": {}},
            effect="read",
            handler=lambda arguments: {"success": True},  # type: ignore[arg-type]
        )
    )
    prepared = registry.prepare({"name": "bad", "arguments": "{}"}).prepared_call

    assert prepared is not None
    result = registry.invoke(prepared)

    assert result.success is False
    assert result.error_code == "invalid_tool_result"
    assert "ToolResult" in (result.error_message or "")
