"""Minimal ToolRegistry for Agent tool preparation and invocation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
from types import MappingProxyType
from typing import Any, Mapping

from scholarlead_agent.agent.tool_types import ToolDefinition, ToolResult


@dataclass(frozen=True)
class ToolContext:
    """Reserved context passed through the tool invocation boundary."""

    workspace: str | None = None
    task_id: str | None = None
    run_id: str | None = None
    identity: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class PreparedToolCall:
    """A validated tool call ready for invocation."""

    tool: ToolDefinition
    name: str
    arguments: dict[str, Any]
    tool_call_id: str | None = None
    context: ToolContext = field(default_factory=ToolContext)


@dataclass(frozen=True)
class ToolPreparationResult:
    """Result of parsing and validating a model tool call."""

    success: bool
    prepared_call: PreparedToolCall | None = None
    error_code: str | None = None
    error_message: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


class ToolRegistry:
    """Register tools and execute prepared tool calls without tool-specific branches."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register one tool definition."""

        _validate_tool_definition(tool)
        if tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def snapshot(self) -> Mapping[str, ToolDefinition]:
        """Return an immutable view of registered tools."""

        return MappingProxyType(dict(self._tools))

    def to_model_tools(self) -> list[dict[str, Any]]:
        """Return model-visible tool schemas without handlers or secrets."""

        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                },
            }
            for tool in sorted(self._tools.values(), key=lambda item: item.name)
        ]

    def prepare(
        self,
        tool_call: dict[str, Any],
        *,
        context: ToolContext | None = None,
    ) -> ToolPreparationResult:
        """Parse and validate a model tool call without executing it."""

        try:
            tool_call_id, tool_name, arguments = _parse_tool_call(tool_call)
        except ValueError as error:
            return _prepare_error("invalid_tool_call", str(error))

        tool = self._tools.get(tool_name)
        if tool is None:
            return _prepare_error("unknown_tool", f"unknown tool: {tool_name}")

        schema_errors = validate_arguments_against_schema(arguments, tool.input_schema)
        if schema_errors:
            return ToolPreparationResult(
                success=False,
                error_code="invalid_arguments",
                error_message=schema_errors[0]["message"],
                errors=schema_errors,
            )

        return ToolPreparationResult(
            success=True,
            prepared_call=PreparedToolCall(
                tool=tool,
                name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
                context=context or ToolContext(),
            ),
        )

    def invoke(
        self,
        prepared_call: PreparedToolCall,
        *,
        context: ToolContext | None = None,
    ) -> ToolResult:
        """Invoke a prepared tool call and normalize unexpected failures."""

        if not isinstance(prepared_call, PreparedToolCall):
            return ToolResult(
                success=False,
                source="tool_registry",
                error_code="invalid_prepared_call",
                error_message="prepared_call must be a PreparedToolCall",
            )

        try:
            result = prepared_call.tool.handler(prepared_call.arguments)
        except Exception as error:
            return ToolResult(
                success=False,
                source=prepared_call.name,
                error_code="tool_execution_error",
                error_message=str(error),
            )

        if not isinstance(result, ToolResult):
            return ToolResult(
                success=False,
                source=prepared_call.name,
                error_code="invalid_tool_result",
                error_message="tool handler must return ToolResult",
            )

        return result


def validate_arguments_against_schema(
    arguments: dict[str, Any],
    schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validate the small JSON Schema subset used by project tools."""

    errors: list[dict[str, Any]] = []
    if schema.get("type") != "object":
        return [{"path": "", "message": "input_schema type must be object"}]
    if not isinstance(arguments, dict):
        return [{"path": "", "message": "arguments must be an object"}]

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return [{"path": "properties", "message": "schema properties must be an object"}]

    required = schema.get("required", [])
    for field_name in required:
        if field_name not in arguments:
            errors.append(
                {"path": field_name, "message": f"{field_name} is required"}
            )

    if schema.get("additionalProperties") is False:
        unexpected = set(arguments) - set(properties)
        for field_name in sorted(unexpected):
            errors.append(
                {
                    "path": field_name,
                    "message": f"unexpected argument: {field_name}",
                }
            )

    for field_name, value in arguments.items():
        field_schema = properties.get(field_name)
        if not isinstance(field_schema, dict):
            continue
        errors.extend(_validate_field(field_name, value, field_schema))

    return errors


def _validate_tool_definition(tool: ToolDefinition) -> None:
    if not isinstance(tool, ToolDefinition):
        raise ValueError("tool must be a ToolDefinition")
    if not tool.name or not tool.name.strip():
        raise ValueError("tool name cannot be empty")
    if not tool.description or not tool.description.strip():
        raise ValueError(f"tool description cannot be empty: {tool.name}")
    if not isinstance(tool.input_schema, dict) or not tool.input_schema:
        raise ValueError(f"tool input_schema must be a non-empty object: {tool.name}")
    if not callable(tool.handler):
        raise ValueError(f"tool handler must be callable: {tool.name}")


def _parse_tool_call(tool_call: dict[str, Any]) -> tuple[str | None, str, dict[str, Any]]:
    if not isinstance(tool_call, dict):
        raise ValueError("tool_call must be an object")

    tool_call_id = tool_call.get("id")
    if tool_call_id is not None and not isinstance(tool_call_id, str):
        raise ValueError("tool_call id must be a string")

    if "function" in tool_call:
        function = tool_call["function"]
        if not isinstance(function, dict):
            raise ValueError("tool_call.function must be an object")
        name = function.get("name")
        raw_arguments = function.get("arguments", "{}")
    else:
        name = tool_call.get("name")
        raw_arguments = tool_call.get("arguments", "{}")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool name is required")

    arguments = _parse_arguments(raw_arguments)
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")

    return tool_call_id, name, arguments


def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
    if isinstance(raw_arguments, dict):
        return raw_arguments
    if not isinstance(raw_arguments, str):
        raise ValueError("arguments must be JSON string or object")
    try:
        parsed = json.loads(raw_arguments)
    except json.JSONDecodeError as error:
        raise ValueError(f"arguments must be valid JSON: {error.msg}") from error
    if not isinstance(parsed, dict):
        raise ValueError("arguments must be an object")
    return parsed


def _validate_field(
    field_name: str,
    value: Any,
    field_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    expected_type = field_schema.get("type")

    if expected_type == "string":
        if not isinstance(value, str):
            return [{"path": field_name, "message": f"{field_name} must be a string"}]
        min_length = field_schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            errors.append(
                {
                    "path": field_name,
                    "message": f"{field_name} must have length at least {min_length}",
                }
            )
        if field_schema.get("format") == "date":
            try:
                date.fromisoformat(value)
            except ValueError:
                errors.append(
                    {
                        "path": field_name,
                        "message": f"{field_name} must be in YYYY-MM-DD format",
                    }
                )

    if expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return [{"path": field_name, "message": f"{field_name} must be an integer"}]
        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")
        if isinstance(minimum, int) and value < minimum:
            errors.append(
                {"path": field_name, "message": f"{field_name} must be >= {minimum}"}
            )
        if isinstance(maximum, int) and value > maximum:
            errors.append(
                {"path": field_name, "message": f"{field_name} must be <= {maximum}"}
            )

    if expected_type == "array":
        if not isinstance(value, list):
            return [{"path": field_name, "message": f"{field_name} must be an array"}]
        item_schema = field_schema.get("items", {})
        if isinstance(item_schema, dict) and item_schema.get("type") == "string":
            for index, item in enumerate(value):
                if not isinstance(item, str):
                    errors.append(
                        {
                            "path": f"{field_name}.{index}",
                            "message": f"{field_name}.{index} must be a string",
                        }
                    )

    return errors


def _prepare_error(error_code: str, message: str) -> ToolPreparationResult:
    return ToolPreparationResult(
        success=False,
        error_code=error_code,
        error_message=message,
        errors=[{"message": message}],
    )
