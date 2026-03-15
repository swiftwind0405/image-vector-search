from dataclasses import dataclass
from pathlib import Path

from image_search_mcp.adapters.embedding.jina import JinaEmbeddingClient
from image_search_mcp.adapters.vector_index.milvus_lite import MilvusLiteIndex
from image_search_mcp.config import Settings
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.services.indexing import IndexService
from image_search_mcp.services.jobs import BackgroundJobWorker, JobRunner
from image_search_mcp.services.search import SearchService
from image_search_mcp.services.status import StatusService


@dataclass(slots=True)
class RuntimeServices:
    search_service: SearchService
    status_service: StatusService
    job_runner: JobRunner
    background_worker: BackgroundJobWorker
    embedding_client: JinaEmbeddingClient
    vector_index: MilvusLiteIndex

    async def aclose(self) -> None:
        try:
            await self.embedding_client.aclose()
        except RuntimeError:
            # Event loop may already be closed during shutdown
            pass
        self.vector_index.close()


def build_runtime_services(settings: Settings) -> RuntimeServices:
    settings.index_root.mkdir(parents=True, exist_ok=True)
    settings.images_root.mkdir(parents=True, exist_ok=True)

    repository = MetadataRepository(_metadata_db_path(settings))
    repository.initialize_schema()

    embedding_client = JinaEmbeddingClient(
        api_key=settings.jina_api_key,
        model=settings.embedding_model,
        version=settings.embedding_version,
    )
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
    job_runner = JobRunner(repository, index_service)
    background_worker = BackgroundJobWorker(job_runner)
    return RuntimeServices(
        search_service=search_service,
        status_service=status_service,
        job_runner=job_runner,
        background_worker=background_worker,
        embedding_client=embedding_client,
        vector_index=vector_index,
    )


def _metadata_db_path(settings: Settings) -> Path:
    return settings.index_root / "metadata.db"
