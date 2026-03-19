import uvicorn

from image_search_mcp.config import Settings

settings = Settings()
uvicorn.run(
    "image_search_mcp.app:create_app",
    factory=True,
    host=settings.host,
    port=settings.port,
)
