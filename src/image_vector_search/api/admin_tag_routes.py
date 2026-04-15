from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from starlette.responses import Response

from image_vector_search.services.tagging import TagService


class CreateTagRequest(BaseModel):
    name: str

class RenameTagRequest(BaseModel):
    name: str

class BatchDeleteTagsRequest(BaseModel):
    tag_ids: list[int]

class AddTagToImageRequest(BaseModel):
    tag_id: int


def create_admin_tag_router(*, tag_service: TagService) -> APIRouter:
    router = APIRouter()

    # --- Tags ---
    @router.post("/api/tags", status_code=201)
    def create_tag(body: CreateTagRequest):
        try:
            tag = tag_service.create_tag(body.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return tag.model_dump()

    @router.get("/api/tags")
    def list_tags():
        return [t.model_dump() for t in tag_service.list_tags()]

    @router.get("/api/tags/export")
    def export_tags():
        md = tag_service.export_tags_markdown()
        return Response(
            content=md,
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=tags.md"},
        )

    @router.post("/api/tags/import")
    async def import_tags(file: UploadFile = File(...)):
        raw = await file.read()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
        result = tag_service.import_tags_markdown(content)
        return result

    @router.put("/api/tags/{tag_id}")
    def rename_tag(tag_id: int, body: RenameTagRequest):
        try:
            tag_service.rename_tag(tag_id, body.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    @router.delete("/api/tags/{tag_id}", status_code=204)
    def delete_tag(tag_id: int):
        tag_service.delete_tag(tag_id)

    @router.post("/api/tags/batch-delete")
    def batch_delete_tags(body: BatchDeleteTagsRequest):
        try:
            deleted = tag_service.bulk_delete_tags(body.tag_ids)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"deleted": deleted}

    # --- Image associations ---
    @router.post("/api/images/{content_hash}/tags", status_code=201)
    def add_tag_to_image(content_hash: str, body: AddTagToImageRequest):
        tag_service.add_tag_to_image(content_hash, body.tag_id)
        return {"ok": True}

    @router.delete("/api/images/{content_hash}/tags/{tag_id}", status_code=204)
    def remove_tag_from_image(content_hash: str, tag_id: int):
        tag_service.remove_tag_from_image(content_hash, tag_id)

    @router.get("/api/images/{content_hash}/tags")
    def get_image_tags(content_hash: str):
        return [t.model_dump() for t in tag_service.get_image_tags(content_hash)]

    return router
