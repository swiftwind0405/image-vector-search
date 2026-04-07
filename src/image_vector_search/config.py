from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMAGE_SEARCH_", extra="ignore")

    app_name: str = "image-vector-search"
    images_root: Path = Path("/data/images")
    index_root: Path = Path("/data/index")
    host: str = "0.0.0.0"
    port: int = 8000
    default_top_k: int = 5
    max_top_k: int = 50
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    jina_api_key: str = ""
    embedding_provider: str = "jina"
    embedding_model: str = "jina-clip-v2"
    embedding_version: str = "v2"
    google_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    embedding_output_dimensionality: int | None = Field(default=None, ge=1)
    embedding_batch_size: int = Field(default=32, ge=1)
    jina_rpm: int = Field(default=100, ge=1, description="Jina API rate limit: requests per minute")
    jina_max_concurrency: int = Field(default=2, ge=1, description="Jina API max concurrent requests")
    vector_index_collection_name: str = "image_embeddings"
    vector_index_db_filename: str = "milvus.db"
    admin_username: str = ""
    admin_password: str = ""
    admin_session_secret: str = ""

    _PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
        "jina": {"embedding_model": "jina-clip-v2", "embedding_version": "v2"},
        "gemini": {"embedding_model": "gemini-embedding-2-preview", "embedding_version": "preview"},
    }

    @field_validator("embedding_provider", mode="before")
    @classmethod
    def _normalize_embedding_provider(cls, value: str) -> str:
        normalized = str(value).strip().lower()
        if normalized not in {"jina", "gemini"}:
            raise ValueError("embedding_provider must be one of: jina, gemini")
        return normalized

    @model_validator(mode="after")
    def _apply_provider_defaults(self) -> "Settings":
        """Apply provider-specific defaults for model/version when they
        still hold the Jina defaults but a different provider is selected."""
        jina_defaults = self._PROVIDER_DEFAULTS["jina"]
        provider_defaults = self._PROVIDER_DEFAULTS.get(self.embedding_provider)
        if provider_defaults and self.embedding_provider != "jina":
            if self.embedding_model == jina_defaults["embedding_model"]:
                self.embedding_model = provider_defaults["embedding_model"]
            if self.embedding_version == jina_defaults["embedding_version"]:
                self.embedding_version = provider_defaults["embedding_version"]
        return self
