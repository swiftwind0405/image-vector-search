from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from image_search_mcp.config import Settings
from image_search_mcp.repositories.sqlite import MetadataRepository


class EmbeddingSettingsResponse(BaseModel):
    provider: str
    jina_api_key_configured: bool
    google_api_key_configured: bool
    using_environment_fallback: bool


class UpdateEmbeddingSettingsRequest(BaseModel):
    provider: Literal["jina", "gemini"]
    jina_api_key: str | None = None
    google_api_key: str | None = None


def create_settings_router(
    *,
    runtime_services,
    repository: MetadataRepository,
    settings: Settings,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/settings/embedding")
    async def get_embedding_settings():
        return JSONResponse(content=jsonable_encoder(_serialize_embedding_settings(repository, settings)))

    @router.put("/api/settings/embedding")
    async def update_embedding_settings(payload: UpdateEmbeddingSettingsRequest):
        db_config = repository.get_embedding_config()
        effective_key = _effective_api_key(
            provider=payload.provider,
            db_config=db_config,
            settings=settings,
            jina_api_key=payload.jina_api_key,
            google_api_key=payload.google_api_key,
        )
        if not effective_key:
            raise HTTPException(
                status_code=422,
                detail=f"No API key configured for provider '{payload.provider}'",
            )

        repository.set_embedding_config(
            provider=payload.provider,
            jina_api_key=payload.jina_api_key,
            google_api_key=payload.google_api_key,
        )

        try:
            await runtime_services.reload_embedding_client()
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Settings saved but embedding reload failed: {exc}",
            ) from exc

        return JSONResponse(content=jsonable_encoder(_serialize_embedding_settings(repository, settings)))

    return router


def _serialize_embedding_settings(
    repository: MetadataRepository,
    settings: Settings,
) -> EmbeddingSettingsResponse:
    db_config = repository.get_embedding_config()
    provider = _effective_provider(db_config, settings)
    return EmbeddingSettingsResponse(
        provider=provider,
        jina_api_key_configured=bool(db_config["jina_api_key"] or settings.jina_api_key),
        google_api_key_configured=bool(db_config["google_api_key"] or settings.google_api_key),
        using_environment_fallback=_using_environment_fallback(
            provider=provider,
            db_config=db_config,
            settings=settings,
        ),
    )


def _effective_provider(db_config: dict[str, str | None], settings: Settings) -> str:
    provider = db_config["provider"] or settings.embedding_provider or ""
    if provider == "jina" and not (db_config["jina_api_key"] or settings.jina_api_key):
        if not (db_config["google_api_key"] or settings.google_api_key):
            return ""
    if provider == "gemini" and not (db_config["google_api_key"] or settings.google_api_key):
        if not (db_config["jina_api_key"] or settings.jina_api_key):
            return ""
    return provider


def _using_environment_fallback(
    *,
    provider: str,
    db_config: dict[str, str | None],
    settings: Settings,
) -> bool:
    if not provider:
        return False
    if provider == "jina":
        return not bool(db_config["jina_api_key"]) and bool(settings.jina_api_key)
    if provider == "gemini":
        return not bool(db_config["google_api_key"]) and bool(settings.google_api_key)
    return False


def _effective_api_key(
    *,
    provider: str,
    db_config: dict[str, str | None],
    settings: Settings,
    jina_api_key: str | None,
    google_api_key: str | None,
) -> str:
    if provider == "jina":
        return jina_api_key or db_config["jina_api_key"] or settings.jina_api_key
    return google_api_key or db_config["google_api_key"] or settings.google_api_key
