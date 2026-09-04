from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateResultPackageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
