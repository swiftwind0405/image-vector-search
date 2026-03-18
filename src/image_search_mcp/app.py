import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

from image_search_mcp.config import Settings
from image_search_mcp.mcp.server import build_mcp_server
from image_search_mcp.runtime import RuntimeServices, build_runtime_services
from image_search_mcp.web.bulk_routes import create_bulk_router
from image_search_mcp.web.routes import create_auth_router, create_web_router
from image_search_mcp.web.tag_routes import create_tag_router


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

    session_secret = app_settings.admin_session_secret or secrets.token_hex(32)
    app.add_middleware(SessionMiddleware, secret_key=session_secret, https_only=False)

    app.include_router(
        create_auth_router(
            admin_username=app_settings.admin_username,
            admin_password=app_settings.admin_password,
        )
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

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

    if runtime_services is not None:
        app.include_router(create_tag_router(tag_service=runtime_services.tag_service))

    if runtime_services is not None:
        app.include_router(
            create_bulk_router(
                tag_service=runtime_services.tag_service,
                images_root=str(app_settings.images_root),
            )
        )

    dist_dir = Path(__file__).with_name("web") / "dist"
    if dist_dir.is_dir():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        spa_index = dist_dir / "index.html"

        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            return FileResponse(str(spa_index))

    return app
