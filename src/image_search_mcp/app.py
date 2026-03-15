from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from image_search_mcp.config import Settings
from image_search_mcp.mcp.server import build_mcp_server
from image_search_mcp.runtime import RuntimeServices, build_runtime_services
from image_search_mcp.web.routes import create_web_router


def create_app(
    settings: Settings | None = None,
    search_service=None,
    status_service=None,
    job_runner=None,
) -> FastAPI:
    app_settings = settings or Settings()
    runtime_services: RuntimeServices | None = None
    if (
        search_service is None
        and status_service is None
        and job_runner is None
    ):
        runtime_services = build_runtime_services(app_settings)
        search_service = runtime_services.search_service
        status_service = runtime_services.status_service
        job_runner = runtime_services.job_runner

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if runtime_services is not None:
            runtime_services.background_worker.start()
        try:
            yield
        finally:
            if runtime_services is not None:
                runtime_services.background_worker.stop()
                await runtime_services.aclose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    static_dir = Path(__file__).with_name("web") / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    if search_service is not None:
        mcp_server = build_mcp_server(search_service)
        app.mount("/mcp", mcp_server.http_app(path="/"))

    if search_service is not None and status_service is not None and job_runner is not None:
        app.include_router(
            create_web_router(
                status_service=status_service,
                job_runner=job_runner,
                search_service=search_service,
            )
        )

    return app
