from __future__ import annotations

from pydantic import BaseModel, Field


class CreateConversationRequest(BaseModel):
    conversation_id: str | None = None
    title: str | None = None


class AddConversationMessageRequest(BaseModel):
    role: str = Field(min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
