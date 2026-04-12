import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import FileResponse

from image_vector_search.adapters.http_tool_adapter import build_tool_router
from image_vector_search.config import Settings
from image_vector_search.services.albums import AlbumService
from image_vector_search.services.tagging import TagService
from image_vector_search.runtime import RuntimeServices, build_runtime_services
from image_vector_search.tools import ToolContext, default_registry
from image_vector_search.api.admin_bulk_routes import create_admin_bulk_router
from image_vector_search.api.admin_album_routes import create_admin_album_router
from image_vector_search.api.admin_folder_routes import create_admin_folder_router
from image_vector_search.api.admin_routes import create_admin_router
from image_vector_search.api.admin_settings_routes import create_admin_settings_router
from image_vector_search.api.admin_tag_routes import create_admin_tag_router
from image_vector_search.api.auth_routes import create_auth_router


def create_app(
    settings: Settings | None = None,
    search_service=None,
    status_service=None,
    job_runner=None,
    tag_service=None,
    album_service=None,
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
        tag_service = runtime_services.tag_service
        album_service = runtime_services.album_service
    elif tag_service is None:
        tag_service = _derive_tag_service(status_service)
    elif album_service is None:
        album_service = _derive_album_service(status_service)

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

    tool_ctx: ToolContext | None = None
    if search_service is not None:
        tool_ctx = ToolContext(
            search_service=search_service,
            tag_service=tag_service,
            status_service=status_service,
            job_runner=job_runner,
            settings=app_settings,
        )
        app.include_router(build_tool_router(default_registry, tool_ctx))

    if search_service is not None and status_service is not None and job_runner is not None:
        app.include_router(
            create_admin_router(
                status_service=status_service,
                job_runner=job_runner,
                search_service=search_service,
            )
        )
    repository = (
        getattr(runtime_services, "repository", None)
        if runtime_services is not None
        else getattr(status_service, "repository", None)
    )
    if runtime_services is not None and repository is not None:
        app.include_router(
            create_admin_settings_router(
                runtime_services=runtime_services,
                repository=repository,
                settings=app_settings,
                status_service=status_service,
            )
        )

    if repository is not None and status_service is not None:
        app.include_router(
            create_admin_folder_router(
                repository=repository,
                status_service=status_service,
                images_root=str(app_settings.images_root),
                auth_enabled=bool(
                    app_settings.admin_username.strip()
                    and app_settings.admin_password.strip()
                ),
            )
        )

    if tag_service is not None:
        app.include_router(create_admin_tag_router(tag_service=tag_service))

    if album_service is not None:
        app.include_router(create_admin_album_router(album_service=album_service))

    if tag_service is not None:
        app.include_router(
            create_admin_bulk_router(
                tag_service=tag_service,
                images_root=str(app_settings.images_root),
            )
        )

    dist_dir = Path(__file__).with_name("frontend") / "dist"
    if dist_dir.is_dir():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        spa_index = dist_dir / "index.html"

        @app.get("/{path:path}")
        async def spa_fallback(path: str):
            return FileResponse(str(spa_index))

    return app


def _derive_tag_service(status_service) -> TagService | None:
    repository = getattr(status_service, "repository", None)
    if repository is None:
        return None
    return TagService(repository=repository)


def _derive_album_service(status_service) -> AlbumService | None:
    repository = getattr(status_service, "repository", None)
    if repository is None:
        return None
    return AlbumService(repository=repository)
