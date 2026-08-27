"""Model-facing contracts for the Agent Loop.

Stage 20D defines the protocol only. Real model adapters are added later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelUsage:
    """Normalized token usage returned by a model provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ModelReply:
    """Normalized reply returned by a model client."""

    content: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: ModelUsage | None = None
    model: str | None = None


class ModelClient(Protocol):
    """Protocol implemented by fake tests and future real model adapters."""

    def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        """Return the next assistant reply."""
