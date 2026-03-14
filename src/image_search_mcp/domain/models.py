from datetime import datetime

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    folder: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)


class SearchResult(BaseModel):
    content_hash: str
    path: str
    score: float
    width: int
    height: int
    mime_type: str


class JobRecord(BaseModel):
    id: str
    job_type: str
    status: str
    requested_at: datetime
