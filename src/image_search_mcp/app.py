from fastapi import FastAPI

from image_search_mcp.config import Settings
from image_search_mcp.mcp.server import build_mcp_server


def create_app(
    settings: Settings | None = None,
    search_service=None,
) -> FastAPI:
    app_settings = settings or Settings()
    app = FastAPI(title=app_settings.app_name)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    if search_service is not None:
        mcp_server = build_mcp_server(search_service)
        app.mount("/mcp", mcp_server.http_app(path="/"))

    return app


app = create_app()
