import uvicorn

from image_vector_search.config import Settings

settings = Settings()
uvicorn.run(
    "image_vector_search.app:create_app",
    factory=True,
    host=settings.host,
    port=settings.port,
)
