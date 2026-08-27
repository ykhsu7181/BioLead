from __future__ import annotations

from pydantic import BaseModel, Field


class CreateResultPackageRequest(BaseModel):
    task_id: str = Field(min_length=1)
    output_dir: str | None = None
