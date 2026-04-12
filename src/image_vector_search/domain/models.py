from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    folder: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)


class Tag(BaseModel):
    id: int
    name: str
    created_at: datetime
    image_count: int | None = None


class Category(BaseModel):
    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: datetime


class CategoryNode(BaseModel):
    """Category with children, for tree responses."""

    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: datetime
    children: list["CategoryNode"] = []
    image_count: int | None = None


class Album(BaseModel):
    id: int
    name: str
    type: Literal["manual", "smart"]
    description: str = ""
    rule_logic: Literal["and", "or"] | None = None
    source_paths: list[str] = []
    image_count: int | None = None
    cover_image: ImageRecord | None = None
    created_at: datetime
    updated_at: datetime


class AlbumRule(BaseModel):
    id: int
    album_id: int
    tag_id: int
    match_mode: Literal["include", "exclude"]
    created_at: datetime
    tag_name: str | None = None


class SearchResult(BaseModel):
    content_hash: str
    path: str
    score: float
    width: int
    height: int
    mime_type: str
    tags: list[Tag] = []
    categories: list[Category] = []


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
    embedding_status: str = "embedded"
    created_at: datetime
    updated_at: datetime


class ImageRecordWithLabels(ImageRecord):
    tags: list[Tag] = []
    categories: list[Category] = []


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
    skipped_oversized: int = 0
    errors: int = 0


class PaginatedImages(BaseModel):
    items: list[ImageRecordWithLabels] = []
    next_cursor: str | None = None


class PaginatedAlbumImages(BaseModel):
    items: list[ImageRecordWithLabels] = []
    next_cursor: str | None = None


class IndexStatus(BaseModel):
    images_on_disk: int
    total_images: int
    active_images: int
    inactive_images: int
    vector_entries: int
    embedding_provider: str
    embedding_model: str
    embedding_version: str
    last_incremental_update_at: datetime | None = None
    last_full_rebuild_at: datetime | None = None
    last_error_summary: str | None = None
