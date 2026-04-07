from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from image_vector_search.services.tagging import TagService


class CreateTagRequest(BaseModel):
    name: str

class RenameTagRequest(BaseModel):
    name: str

class CreateCategoryRequest(BaseModel):
    name: str
    parent_id: int | None = None

class UpdateCategoryRequest(BaseModel):
    name: str | None = None
    move_to_parent_id: int | None = None
    move_to_root: bool = False

class BatchDeleteTagsRequest(BaseModel):
    tag_ids: list[int]

class BatchDeleteCategoriesRequest(BaseModel):
    category_ids: list[int]

class AddTagToImageRequest(BaseModel):
    tag_id: int

class AddImageToCategoryRequest(BaseModel):
    category_id: int


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

    # --- Categories ---
    @router.post("/api/categories", status_code=201)
    def create_category(body: CreateCategoryRequest):
        try:
            cat = tag_service.create_category(body.name, parent_id=body.parent_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return cat.model_dump()

    @router.get("/api/categories")
    def get_category_tree():
        tree = tag_service.get_category_tree()
        return [n.model_dump() for n in tree]

    @router.get("/api/categories/{category_id}/children")
    def get_category_children(category_id: int):
        children = tag_service.list_categories(parent_id=category_id)
        return [c.model_dump() for c in children]

    @router.put("/api/categories/{category_id}")
    def update_category(category_id: int, body: UpdateCategoryRequest):
        try:
            if body.name is not None:
                tag_service.rename_category(category_id, body.name)
            if body.move_to_root:
                tag_service.move_category(category_id, None)
            elif body.move_to_parent_id is not None:
                tag_service.move_category(category_id, body.move_to_parent_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    @router.delete("/api/categories/{category_id}", status_code=204)
    def delete_category(category_id: int):
        tag_service.delete_category(category_id)

    @router.post("/api/categories/batch-delete")
    def batch_delete_categories(body: BatchDeleteCategoriesRequest):
        try:
            deleted = tag_service.bulk_delete_categories(body.category_ids)
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

    @router.post("/api/images/{content_hash}/categories", status_code=201)
    def add_image_to_category(content_hash: str, body: AddImageToCategoryRequest):
        tag_service.add_image_to_category(content_hash, body.category_id)
        return {"ok": True}

    @router.delete("/api/images/{content_hash}/categories/{category_id}", status_code=204)
    def remove_image_from_category(content_hash: str, category_id: int):
        tag_service.remove_image_from_category(content_hash, category_id)

    @router.get("/api/images/{content_hash}/categories")
    def get_image_categories(content_hash: str):
        return [c.model_dump() for c in tag_service.get_image_categories(content_hash)]

    return router
