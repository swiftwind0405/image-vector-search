import json
from datetime import UTC, datetime
from pathlib import Path

from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord, IndexingReport
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.services.jobs import JobRunner
from image_search_mcp.services.status import StatusService


class FakeIndexService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail_job_type: str | None = None

    def run_incremental_update(self) -> IndexingReport:
        self.calls.append("incremental")
        if self.fail_job_type == "incremental":
            raise RuntimeError("incremental failed")
        return IndexingReport(scanned=10, added=1, reused=9)

    def run_full_rebuild(self) -> IndexingReport:
        self.calls.append("full_rebuild")
        if self.fail_job_type == "full_rebuild":
            raise RuntimeError("full rebuild failed")
        return IndexingReport(scanned=12, added=2, reused=10)


class FakeVectorIndex:
    def __init__(self, count_value: int) -> None:
        self.count_value = count_value
        self.embedding_keys: list[str] = []

    def count(self, embedding_key: str) -> int:
        self.embedding_keys.append(embedding_key)
        return self.count_value


def test_job_runner_serializes_index_jobs(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = FakeIndexService()
    job_runner = JobRunner(repository, index_service)

    first = job_runner.enqueue("incremental")
    second = job_runner.enqueue("full_rebuild")

    assert first.status == "queued"
    assert second.status == "queued"

    job_runner.run_next()
    job_runner.run_next()

    first_job = repository.get_job(first.id)
    second_job = repository.get_job(second.id)
    assert first_job is not None
    assert second_job is not None
    assert first_job.status == "succeeded"
    assert second_job.status == "succeeded"
    assert json.loads(first_job.summary_json or "{}")["added"] == 1
    assert json.loads(second_job.summary_json or "{}")["added"] == 2
    assert index_service.calls == ["incremental", "full_rebuild"]


def test_job_runner_marks_failed_job_and_updates_last_error_summary(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = FakeIndexService()
    index_service.fail_job_type = "full_rebuild"
    job_runner = JobRunner(repository, index_service)

    job = job_runner.enqueue("full_rebuild")
    job_runner.run_next()

    stored_job = repository.get_job(job.id)
    assert stored_job is not None
    assert stored_job.status == "failed"
    assert stored_job.error_text == "full rebuild failed"
    assert repository.get_system_state("last_error_summary") == "full rebuild failed"


def test_status_service_reads_status_snapshot_and_recent_jobs(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    settings = Settings(
        images_root=tmp_path / "images",
        index_root=tmp_path / "index",
        embedding_provider="fake",
        embedding_model="fake-clip",
        embedding_version="2026-03",
    )
    now = datetime.now(UTC)
    repository.upsert_image(
        ImageRecord(
            content_hash="hash-a",
            canonical_path="/data/images/a.jpg",
            file_size=10,
            mtime=1.0,
            mime_type="image/jpeg",
            width=10,
            height=10,
            is_active=True,
            last_seen_at=now,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            created_at=now,
            updated_at=now,
        )
    )
    repository.upsert_image(
        ImageRecord(
            content_hash="hash-b",
            canonical_path="/data/images/b.jpg",
            file_size=10,
            mtime=1.0,
            mime_type="image/jpeg",
            width=10,
            height=10,
            is_active=False,
            last_seen_at=now,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            created_at=now,
            updated_at=now,
        )
    )
    repository.set_system_state("last_incremental_update_at", now.isoformat())
    repository.set_system_state("last_full_rebuild_at", now.isoformat())
    repository.set_system_state("last_error_summary", "none")

    job_runner = JobRunner(repository, FakeIndexService())
    job_runner.enqueue("incremental")

    status_service = StatusService(
        settings=settings,
        repository=repository,
        vector_index=FakeVectorIndex(count_value=7),
    )

    snapshot = status_service.get_index_status()
    jobs = status_service.list_recent_jobs(limit=5)

    assert snapshot.total_images == 2
    assert snapshot.active_images == 1
    assert snapshot.inactive_images == 1
    assert snapshot.vector_entries == 7
    assert snapshot.embedding_provider == "fake"
    assert snapshot.embedding_model == "fake-clip"
    assert snapshot.embedding_version == "2026-03"
    assert snapshot.last_error_summary == "none"
    assert len(jobs) == 1
    assert jobs[0].status == "queued"
