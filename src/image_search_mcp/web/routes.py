from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field


TEMPLATES = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))


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

    @router.get("/", response_class=HTMLResponse)
    async def admin_home(request: Request):
        snapshot = status_service.get_index_status()
        jobs = status_service.list_recent_jobs(limit=10)
        return TEMPLATES.TemplateResponse(
            request,
            "index.html",
            {
                "request": request,
                "snapshot": snapshot,
                "jobs": jobs,
            },
        )

    @router.get("/api/status")
    async def get_status():
        return JSONResponse(jsonable_encoder(status_service.get_index_status()))

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

    return router
