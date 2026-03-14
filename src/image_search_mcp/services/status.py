from datetime import datetime

from image_search_mcp.domain.models import IndexStatus


class StatusService:
    def __init__(self, *, settings, repository, vector_index) -> None:
        self.settings = settings
        self.repository = repository
        self.vector_index = vector_index

    def get_index_status(self) -> IndexStatus:
        aggregates = self.repository.read_status_aggregates()
        return IndexStatus(
            total_images=aggregates.total_images,
            active_images=aggregates.active_images,
            inactive_images=aggregates.inactive_images,
            vector_entries=self.vector_index.count(self._embedding_key()),
            embedding_provider=self.settings.embedding_provider,
            embedding_model=self.settings.embedding_model,
            embedding_version=self.settings.embedding_version,
            last_incremental_update_at=self._read_datetime("last_incremental_update_at"),
            last_full_rebuild_at=self._read_datetime("last_full_rebuild_at"),
            last_error_summary=self.repository.get_system_state("last_error_summary"),
        )

    def list_recent_jobs(self, limit: int = 20):
        return self.repository.list_recent_jobs(limit=limit)

    def get_job(self, job_id: str):
        return self.repository.get_job(job_id)

    def _embedding_key(self) -> str:
        return (
            f"{self.settings.embedding_provider}:"
            f"{self.settings.embedding_model}:"
            f"{self.settings.embedding_version}"
        )

    def _read_datetime(self, key: str) -> datetime | None:
        value = self.repository.get_system_state(key)
        if value is None:
            return None
        return datetime.fromisoformat(value)
