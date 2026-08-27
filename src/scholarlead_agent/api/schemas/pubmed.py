from __future__ import annotations

from pydantic import BaseModel, Field


class PubMedSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    from_date: str = Field(min_length=10, max_length=10)
    to_date: str = Field(min_length=10, max_length=10)
    max_results: int = Field(ge=1, le=20)
    country: str | None = None
    service_type: str | None = None
    raw_dir: str = "data/raw/pubmed"
    processed_dir: str = "data/processed/pubmed"
