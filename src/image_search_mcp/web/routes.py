import io
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
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


def create_web_router(*, status_service, job_runner, search_service) -> APIRouter:
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
    async def list_images(folder: str | None = None):
        return JSONResponse(
            content=jsonable_encoder(status_service.list_active_images_with_labels(folder=folder))
        )

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
        results = await search_service.search_images(**payload.model_dump())
        return JSONResponse(content={"results": jsonable_encoder(results)})

    @router.post("/api/debug/search/similar")
    async def debug_similar_search(payload: DebugSimilarSearchRequest):
        results = await search_service.search_similar(**payload.model_dump())
        return JSONResponse(content={"results": jsonable_encoder(results)})

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
