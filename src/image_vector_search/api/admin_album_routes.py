from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from image_vector_search.services.albums import AlbumService


class CreateAlbumRequest(BaseModel):
    name: str
    type: str
    description: str | None = None
    rule_logic: str | None = None


class UpdateAlbumRequest(BaseModel):
    name: str
    description: str | None = None


class AddImagesRequest(BaseModel):
    content_hashes: list[str]


class RemoveImagesRequest(BaseModel):
    content_hashes: list[str]


class AlbumRuleInput(BaseModel):
    tag_id: int
    match_mode: str


class SetRulesRequest(BaseModel):
    rules: list[AlbumRuleInput]


class SetSourcePathsRequest(BaseModel):
    paths: list[str]


def create_admin_album_router(*, album_service: AlbumService) -> APIRouter:
    router = APIRouter()

    @router.post("/api/albums", status_code=201)
    def create_album(body: CreateAlbumRequest):
        try:
            album = album_service.create_album(
                name=body.name,
                album_type=body.type,
                description=body.description,
                rule_logic=body.rule_logic,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return album.model_dump(mode="json")

    @router.get("/api/albums")
    def list_albums():
        return [album.model_dump(mode="json") for album in album_service.list_albums()]

    @router.get("/api/albums/{album_id}")
    def get_album(album_id: int):
        album = album_service.get_album(album_id)
        if album is None:
            raise HTTPException(status_code=404, detail="Album not found")
        return album.model_dump(mode="json")

    @router.put("/api/albums/{album_id}")
    def update_album(album_id: int, body: UpdateAlbumRequest):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            album = album_service.update_album(
                album_id=album_id,
                name=body.name,
                description=body.description,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        if album is None:
            raise HTTPException(status_code=404, detail="Album not found")
        return album.model_dump(mode="json")

    @router.delete("/api/albums/{album_id}", status_code=204)
    def delete_album(album_id: int):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        album_service.delete_album(album_id)

    @router.get("/api/albums/{album_id}/images")
    def list_album_images(album_id: int, limit: int | None = None, cursor: str | None = None):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            page = album_service.list_album_images(album_id, limit=limit, cursor=cursor)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return page.model_dump(mode="json")

    @router.post("/api/albums/{album_id}/images")
    def add_images_to_album(album_id: int, body: AddImagesRequest):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            added = album_service.add_images_to_album(album_id, body.content_hashes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return {"added": added}

    @router.delete("/api/albums/{album_id}/images")
    def remove_images_from_album(album_id: int, body: RemoveImagesRequest):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            removed = album_service.remove_images_from_album(album_id, body.content_hashes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"removed": removed}

    @router.get("/api/albums/{album_id}/rules")
    def get_album_rules(album_id: int):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        return [rule.model_dump(mode="json") for rule in album_service.get_album_rules(album_id)]

    @router.put("/api/albums/{album_id}/rules")
    def set_album_rules(album_id: int, body: SetRulesRequest):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            album_service.set_album_rules(
                album_id,
                [rule.model_dump() for rule in body.rules],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True}

    @router.get("/api/albums/{album_id}/source-paths")
    def get_album_source_paths(album_id: int):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        return album_service.get_album_source_paths(album_id)

    @router.put("/api/albums/{album_id}/source-paths")
    def set_album_source_paths(album_id: int, body: SetSourcePathsRequest):
        if album_service.get_album(album_id) is None:
            raise HTTPException(status_code=404, detail="Album not found")
        try:
            album_service.set_album_source_paths(album_id, body.paths)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        return {"ok": True}

    return router
