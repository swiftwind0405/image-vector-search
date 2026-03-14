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
    started_at: datetime | None = None
    finished_at: datetime | None = None
    summary_json: str | None = None
    error_text: str | None = None


class ImageRecord(BaseModel):
    content_hash: str
    canonical_path: str
    file_size: int
    mtime: float
    mime_type: str
    width: int
    height: int
    is_active: bool
    last_seen_at: datetime
    embedding_provider: str
    embedding_model: str
    embedding_version: str
    created_at: datetime
    updated_at: datetime


class ImagePathRecord(BaseModel):
    content_hash: str
    path: str
    file_size: int
    mtime: float
    is_active: bool
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class StatusAggregates(BaseModel):
    total_images: int
    active_images: int
    inactive_images: int


class IndexingReport(BaseModel):
    scanned: int = 0
    added: int = 0
    reused: int = 0
    path_updated: int = 0
    deactivated: int = 0
    skipped: int = 0
    errors: int = 0
