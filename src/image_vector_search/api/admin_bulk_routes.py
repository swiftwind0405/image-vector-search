from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from image_vector_search.services.tagging import TagService


class BulkTagRequest(BaseModel):
    content_hashes: list[str]
    tag_id: int


class BulkCategoryRequest(BaseModel):
    content_hashes: list[str]
    category_id: int


class FolderTagRequest(BaseModel):
    folder: str
    tag_id: int


class FolderCategoryRequest(BaseModel):
    folder: str
    category_id: int


class FilePathRequest(BaseModel):
    path: str


def create_admin_bulk_router(*, tag_service: TagService, images_root: str) -> APIRouter:
    router = APIRouter()
    root_path = Path(images_root).resolve()

    # --- Folder listing ---

    @router.get("/api/folders")
    def list_folders():
        return tag_service._repo.list_folders(images_root)

    # --- Bulk by selection ---

    @router.post("/api/bulk/tags/add")
    def bulk_add_tags(body: BulkTagRequest):
        if len(body.content_hashes) > TagService.MAX_BULK_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"content_hashes exceeds maximum of {TagService.MAX_BULK_SIZE}",
            )
        try:
            affected = tag_service.bulk_add_tag(body.content_hashes, body.tag_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/tags/remove")
    def bulk_remove_tags(body: BulkTagRequest):
        if len(body.content_hashes) > TagService.MAX_BULK_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"content_hashes exceeds maximum of {TagService.MAX_BULK_SIZE}",
            )
        try:
            affected = tag_service.bulk_remove_tag(body.content_hashes, body.tag_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/categories/add")
    def bulk_add_categories(body: BulkCategoryRequest):
        if len(body.content_hashes) > TagService.MAX_BULK_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"content_hashes exceeds maximum of {TagService.MAX_BULK_SIZE}",
            )
        try:
            affected = tag_service.bulk_add_category(body.content_hashes, body.category_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/categories/remove")
    def bulk_remove_categories(body: BulkCategoryRequest):
        if len(body.content_hashes) > TagService.MAX_BULK_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"content_hashes exceeds maximum of {TagService.MAX_BULK_SIZE}",
            )
        try:
            affected = tag_service.bulk_remove_category(body.content_hashes, body.category_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    # --- Bulk by folder ---

    @router.post("/api/bulk/folder/tags/add")
    def bulk_folder_add_tags(body: FolderTagRequest):
        try:
            affected = tag_service.bulk_folder_add_tag(body.folder, body.tag_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/tags/remove")
    def bulk_folder_remove_tags(body: FolderTagRequest):
        try:
            affected = tag_service.bulk_folder_remove_tag(body.folder, body.tag_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/categories/add")
    def bulk_folder_add_categories(body: FolderCategoryRequest):
        try:
            affected = tag_service.bulk_folder_add_category(
                body.folder, body.category_id, images_root
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/categories/remove")
    def bulk_folder_remove_categories(body: FolderCategoryRequest):
        try:
            affected = tag_service.bulk_folder_remove_category(
                body.folder, body.category_id, images_root
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    # --- File operations ---

    def _resolve_and_validate(path: str) -> Path:
        resolved = Path(path).resolve()
        if not resolved.is_relative_to(root_path):
            raise HTTPException(status_code=400, detail="Path is outside the images root")
        if not resolved.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return resolved

    @router.post("/api/files/open")
    async def open_file(body: FilePathRequest):
        resolved = _resolve_and_validate(body.path)

        def _open():
            if sys.platform == "darwin":
                return subprocess.run(["open", str(resolved)], capture_output=True)
            else:
                return subprocess.run(["xdg-open", str(resolved)], capture_output=True)

        result = await asyncio.to_thread(_open)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Failed to open file")
        return {"ok": True}

    @router.post("/api/files/reveal")
    async def reveal_file(body: FilePathRequest):
        resolved = _resolve_and_validate(body.path)

        def _reveal():
            if sys.platform == "darwin":
                return subprocess.run(["open", "-R", str(resolved)], capture_output=True)
            else:
                return subprocess.run(
                    ["xdg-open", str(resolved.parent)], capture_output=True
                )

        result = await asyncio.to_thread(_reveal)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail="Failed to reveal file")
        return {"ok": True}

    return router
