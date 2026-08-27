from __future__ import annotations

from pydantic import BaseModel, Field


class JobItemRequest(BaseModel):
    lead_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class CreateJobRequest(BaseModel):
    job_type: str = Field(min_length=1)
    task_id: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    items: list[JobItemRequest] = Field(default_factory=list)


class RetryJobRequest(BaseModel):
    job_item_id: str = Field(min_length=1)
