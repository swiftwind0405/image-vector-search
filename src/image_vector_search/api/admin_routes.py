import io
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field


class DebugTextSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1)
    min_score: float = 0.0
    folder: str | None = None


class DebugSimilarSearchRequest(BaseModel):
    image_path: str
    top_k: int = Field(default=5, ge=1)
    min_score: float = 0.0
    folder: str | None = None


class PurgeInactiveImagesRequest(BaseModel):
    content_hashes: list[str] = Field(default_factory=list)


def create_admin_router(*, status_service, job_runner, search_service) -> APIRouter:
    router = APIRouter()

    @router.get("/api/status")
    async def get_status():
        return JSONResponse(jsonable_encoder(await status_service.get_index_status()))

    @router.post("/api/jobs/incremental", status_code=status.HTTP_202_ACCEPTED)
    async def enqueue_incremental_job():
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=jsonable_encoder(job_runner.enqueue("incremental")),
        )

    @router.post("/api/jobs/rebuild", status_code=status.HTTP_202_ACCEPTED)
    async def enqueue_rebuild_job():
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=jsonable_encoder(job_runner.enqueue("full_rebuild")),
        )

    @router.get("/api/images")
    async def list_images(
        folder: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
    ):
        return JSONResponse(
            content=jsonable_encoder(
                status_service.list_active_images_with_labels(
                    folder=folder,
                    tag_id=tag_id,
                    category_id=category_id,
                    include_descendants=include_descendants,
                )
            )
        )

    @router.get("/api/images/inactive")
    async def list_inactive_images():
        return JSONResponse(content=jsonable_encoder(status_service.list_inactive_images()))

    @router.post("/api/images/inactive/purge")
    async def purge_inactive_images(payload: PurgeInactiveImagesRequest):
        try:
            affected = status_service.purge_inactive_images(payload.content_hashes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(content={"ok": True, "affected": affected})

    @router.get("/api/jobs")
    async def list_jobs():
        return JSONResponse(
            content=jsonable_encoder(status_service.list_recent_jobs(limit=20))
        )

    @router.get("/api/jobs/{job_id}")
    async def get_job(job_id: str):
        job = status_service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return JSONResponse(content=jsonable_encoder(job))

    @router.post("/api/debug/search/text")
    async def debug_text_search(payload: DebugTextSearchRequest):
        try:
            results = await search_service.search_images(**payload.model_dump())
        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to connect to embedding service: {exc}",
            ) from exc
        return JSONResponse(content={"results": jsonable_encoder(results)})

    @router.post("/api/debug/search/similar")
    async def debug_similar_search(payload: DebugSimilarSearchRequest):
        try:
            results = await search_service.search_similar(**payload.model_dump())
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return JSONResponse(content={"results": jsonable_encoder(results)})

    @router.get("/api/images/{content_hash}/file")
    async def get_image_file(content_hash: str):
        image_record = status_service.get_image(content_hash)
        if image_record is None:
            raise HTTPException(status_code=404, detail="not found")
        file_path = Path(image_record.canonical_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="not found")
        return FileResponse(
            path=str(file_path),
            media_type=image_record.mime_type or "application/octet-stream",
            headers={"Cache-Control": "max-age=86400"},
        )

    @router.get("/api/images/{content_hash}/thumbnail")
    async def get_thumbnail(content_hash: str, size: int = 120):
        if size < 50 or size > 500:
            raise HTTPException(status_code=422, detail="size must be between 50 and 500")
        image_record = status_service.get_image(content_hash)
        if image_record is None:
            raise HTTPException(status_code=404, detail="not found")
        file_path = Path(image_record.canonical_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="not found")
        try:
            from PIL import Image as PILImage
            with PILImage.open(file_path) as img:
                img.thumbnail((size, size))
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=75)
                buf.seek(0)
                return Response(
                    content=buf.read(),
                    media_type="image/jpeg",
                    headers={"Cache-Control": "max-age=86400"},
                )
        except Exception:
            raise HTTPException(status_code=404, detail="not found")

    return router
