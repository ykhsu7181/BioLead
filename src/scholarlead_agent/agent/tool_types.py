"""Minimal tool contracts used before the full ToolRegistry stage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal


ToolEffect = Literal["read", "write", "execute", "external"]


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by an Agent Tool."""

    success: bool
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    persistence_payload: Any | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class ToolDefinition:
    """Minimal tool definition without implementing a registry."""

    name: str
    description: str
    input_schema: dict[str, Any]
    effect: ToolEffect
    handler: Callable[[dict[str, Any]], ToolResult]
