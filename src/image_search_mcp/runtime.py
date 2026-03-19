from dataclasses import dataclass
from pathlib import Path

from image_search_mcp.adapters.embedding.jina import JinaEmbeddingClient
from image_search_mcp.adapters.embedding.rate_limiter import AdaptiveRateLimiter
from image_search_mcp.adapters.vector_index.milvus_lite import MilvusLiteIndex
from image_search_mcp.config import Settings
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.services.indexing import IndexService
from image_search_mcp.services.jobs import BackgroundJobWorker, JobRunner
from image_search_mcp.services.search import SearchService
from image_search_mcp.services.status import StatusService
from image_search_mcp.services.tagging import TagService


@dataclass(slots=True)
class RuntimeServices:
    search_service: SearchService
    status_service: StatusService
    job_runner: JobRunner
    background_worker: BackgroundJobWorker
    embedding_client: JinaEmbeddingClient
    index_embedding_client: JinaEmbeddingClient
    vector_index: MilvusLiteIndex
    tag_service: TagService

    async def aclose(self) -> None:
        for client in (self.embedding_client, self.index_embedding_client):
            try:
                await client.aclose()
            except RuntimeError:
                pass
        self.vector_index.close()


def build_runtime_services(settings: Settings) -> RuntimeServices:
    settings.index_root.mkdir(parents=True, exist_ok=True)
    settings.images_root.mkdir(parents=True, exist_ok=True)

    repository = MetadataRepository(_metadata_db_path(settings))
    repository.initialize_schema()

    rate_limiter = AdaptiveRateLimiter(
        rpm=settings.jina_rpm,
        max_concurrency=settings.jina_max_concurrency,
    )
    embedding_client = JinaEmbeddingClient(
        api_key=settings.jina_api_key,
        model=settings.embedding_model,
        version=settings.embedding_version,
        rate_limiter=rate_limiter,
    )
    index_embedding_client = JinaEmbeddingClient(
        api_key=settings.jina_api_key,
        model=settings.embedding_model,
        version=settings.embedding_version,
        rate_limiter=rate_limiter,
    )
    vector_index = MilvusLiteIndex(
        db_path=settings.index_root / settings.vector_index_db_filename,
        collection_name=settings.vector_index_collection_name,
    )

    index_service = IndexService(
        settings=settings,
        repository=repository,
        embedding_client=index_embedding_client,
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
    job_runner = JobRunner(repository, index_service)
    background_worker = BackgroundJobWorker(job_runner)
    return RuntimeServices(
        search_service=search_service,
        status_service=status_service,
        job_runner=job_runner,
        background_worker=background_worker,
        embedding_client=embedding_client,
        index_embedding_client=index_embedding_client,
        vector_index=vector_index,
        tag_service=tag_service,
    )


def _metadata_db_path(settings: Settings) -> Path:
    return settings.index_root / "metadata.db"
