"""Schemas for the synchronous Agent execution API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AgentRunRequest(BaseModel):
    """Minimal natural-language Agent request."""

    model_config = ConfigDict(extra="forbid")

    message: str | None = None
    conversation_id: str | None = None
    max_turns: int | None = 6
    idempotency_key: str | None = None
