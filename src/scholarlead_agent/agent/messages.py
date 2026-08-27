"""Message helpers for the Agent Loop."""

from __future__ import annotations

import json
from typing import Any

from scholarlead_agent.agent.tool_types import ToolResult


def system_message(content: str) -> dict[str, Any]:
    return {"role": "system", "content": content}


def user_message(content: str) -> dict[str, Any]:
    return {"role": "user", "content": content}


def assistant_message(
    *,
    content: str | None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": content or ""}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def tool_message(
    *,
    tool_call_id: str,
    name: str,
    result: ToolResult,
) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": json.dumps(tool_result_to_dict(result), ensure_ascii=False),
    }


def tool_result_to_dict(result: ToolResult) -> dict[str, Any]:
    return {
        "success": result.success,
        "source": result.source,
        "data": result.data,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "errors": result.errors,
    }
