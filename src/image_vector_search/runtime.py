from dataclasses import dataclass
from pathlib import Path

from image_vector_search.adapters.embedding.base import EmbeddingClient
from image_vector_search.adapters.embedding.gemini import GeminiEmbeddingClient
from image_vector_search.adapters.embedding.jina import JinaEmbeddingClient
from image_vector_search.adapters.embedding.rate_limiter import AdaptiveRateLimiter
from image_vector_search.adapters.vector_index.milvus_lite import MilvusLiteIndex
from image_vector_search.config import Settings
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.albums import AlbumService
from image_vector_search.services.indexing import IndexService
from image_vector_search.services.jobs import BackgroundJobWorker, JobRunner
from image_vector_search.services.search import SearchService
from image_vector_search.services.status import StatusService
from image_vector_search.services.tagging import TagService


@dataclass(slots=True)
class RuntimeServices:
    search_service: SearchService
    status_service: StatusService
    job_runner: JobRunner
    background_worker: BackgroundJobWorker
    embedding_client: EmbeddingClient | None
    vector_index: MilvusLiteIndex
    tag_service: TagService
    album_service: AlbumService
    index_service: IndexService
    repository: MetadataRepository
    settings: Settings

    async def aclose(self) -> None:
        if self.embedding_client is not None:
            try:
                await self.embedding_client.aclose()
            except RuntimeError:
                pass
        self.vector_index.close()

    async def reload_embedding_client(self) -> None:
        provider, api_key = _resolve_embedding_selection(
            repository=self.repository,
            settings=self.settings,
        )
        if not provider or not api_key:
            raise ValueError("Embedding not configured")

        new_client = _build_embedding_client_from(provider, api_key, self.settings)
        if new_client is None:
            raise ValueError("Embedding not configured")

        old_client = self.embedding_client
        self.embedding_client = new_client
        self.settings.embedding_provider = provider
        self.search_service.embedding_client = new_client
        self.index_service.embedding_client = new_client

        if old_client is None:
            return
        try:
            await old_client.aclose()
        except Exception:
            pass


def build_runtime_services(settings: Settings) -> RuntimeServices:
    settings.index_root.mkdir(parents=True, exist_ok=True)
    settings.images_root.mkdir(parents=True, exist_ok=True)

    repository = MetadataRepository(_metadata_db_path(settings))
    repository.initialize_schema()

    provider, api_key = _resolve_embedding_selection(repository=repository, settings=settings)
    embedding_client = None
    if provider or api_key:
        embedding_client = _build_embedding_client_from(provider, api_key, settings)
        settings.embedding_provider = provider
    vector_index = MilvusLiteIndex(
        db_path=settings.index_root / settings.vector_index_db_filename,
        collection_name=settings.vector_index_collection_name,
    )

    index_service = IndexService(
        settings=settings,
        repository=repository,
        embedding_client=embedding_client,
        vector_index=vector_index,
    )
    search_service = SearchService(
        settings=settings,
        repository=repository,
        embedding_client=embedding_client,
        vector_index=vector_index,
    )
    status_service = StatusService(
        settings=settings,
        repository=repository,
        vector_index=vector_index,
    )
    tag_service = TagService(repository=repository)
    album_service = AlbumService(repository=repository)
    job_runner = JobRunner(repository, index_service)
    background_worker = BackgroundJobWorker(job_runner)
    return RuntimeServices(
        search_service=search_service,
        status_service=status_service,
        job_runner=job_runner,
        background_worker=background_worker,
        embedding_client=embedding_client,
        vector_index=vector_index,
        tag_service=tag_service,
        album_service=album_service,
        index_service=index_service,
        repository=repository,
        settings=settings,
    )


def _metadata_db_path(settings: Settings) -> Path:
    return settings.index_root / "metadata.db"


def _build_embedding_client(settings: Settings) -> EmbeddingClient:
    provider = settings.embedding_provider
    if provider == "jina" and not settings.jina_api_key:
        raise ValueError("jina_api_key is required when embedding_provider='jina'")
    if provider == "gemini" and not settings.google_api_key:
        raise ValueError("google_api_key is required when embedding_provider='gemini'")

    return _build_embedding_client_from(
        provider,
        settings.jina_api_key if provider == "jina" else settings.google_api_key,
        settings,
    )


def _build_embedding_client_from(
    provider: str,
    api_key: str,
    settings: Settings,
) -> EmbeddingClient | None:
    if not provider or not api_key:
        return None

    if provider == "jina":
        rate_limiter = AdaptiveRateLimiter(
            rpm=settings.jina_rpm,
            max_concurrency=settings.jina_max_concurrency,
        )
        return JinaEmbeddingClient(
            api_key=api_key,
            model=settings.embedding_model,
            version=settings.embedding_version,
            rate_limiter=rate_limiter,
        )

    if provider == "gemini":
        return GeminiEmbeddingClient(
            api_key=api_key,
            model=settings.embedding_model,
            version=settings.embedding_version,
            output_dimensionality=settings.embedding_output_dimensionality,
            base_url=settings.gemini_base_url,
            batch_size=settings.embedding_batch_size,
        )

    raise ValueError(f"Unsupported embedding_provider: {provider}")


def _resolve_embedding_selection(
    *,
    repository: MetadataRepository,
    settings: Settings,
) -> tuple[str, str]:
    db_config = repository.get_embedding_config()
    db_has_any_value = any(value is not None for value in db_config.values())

    if not db_has_any_value and not settings.jina_api_key and not settings.google_api_key:
        return "", ""

    provider = db_config["provider"] or settings.embedding_provider
    api_key = ""
    if provider == "jina":
        api_key = db_config["jina_api_key"] or settings.jina_api_key
    elif provider == "gemini":
        api_key = db_config["google_api_key"] or settings.google_api_key
    return provider or "", api_key or ""
