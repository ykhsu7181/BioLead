from __future__ import annotations

from pydantic import BaseModel, Field


class BatchDraftRequest(BaseModel):
    lead_ids: list[str] = Field(default_factory=list)
    task_id: str | None = None
    max_items: int = Field(default=10, ge=1, le=50)


class BatchReviewRequest(BaseModel):
    draft_ids: list[str] = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    comments: str | None = None


class BatchSendRequest(BaseModel):
    draft_ids: list[str] = Field(min_length=1)
    actor: str = Field(min_length=1)
    mode: str = "permission_check"
    max_items: int = Field(default=5, ge=1, le=50)
