from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMAGE_SEARCH_", extra="ignore")

    app_name: str = "image-search-mcp"
    images_root: Path = Path("/data/images")
    index_root: Path = Path("/data/index")
    host: str = "0.0.0.0"
    port: int = 8000
    default_top_k: int = 5
    max_top_k: int = 50
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    jina_api_key: str = ""
    embedding_model: str = "jina-clip-v2"
    embedding_version: str = "v2"
    embedding_batch_size: int = Field(default=32, ge=1)
