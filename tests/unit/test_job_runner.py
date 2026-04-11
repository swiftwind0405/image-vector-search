import json
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread

import pytest

from image_vector_search.config import Settings
from image_vector_search.domain.models import ImageRecord, IndexingReport
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.jobs import BackgroundJobWorker, JobRunner
from image_vector_search.services.status import StatusService


class FakeIndexService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.fail_job_type: str | None = None
        self.embed_selected_payloads: list[list[str]] = []

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

    def force_embed_images(self, content_hashes: list[str]) -> dict:
        self.calls.append("embed_selected")
        self.embed_selected_payloads.append(list(content_hashes))
        if self.fail_job_type == "embed_selected":
            raise RuntimeError("embed selected failed")
        return {"succeeded": len(content_hashes), "failed": 0, "errors": []}


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


def test_job_runner_clears_last_error_summary_after_clean_success(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    repository.set_system_state("last_error_summary", "stale error")
    index_service = FakeIndexService()
    job_runner = JobRunner(repository, index_service)

    job_runner.enqueue("full_rebuild")
    job_runner.run_next()

    assert repository.get_system_state("last_error_summary") is None


def test_job_runner_runs_embed_selected_jobs_with_payload(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = FakeIndexService()
    job_runner = JobRunner(repository, index_service)

    job = job_runner.enqueue(
        "embed_selected",
        payload={"content_hashes": ["hash-a", "hash-b"]},
    )
    job_runner.run_next()

    stored_job = repository.get_job(job.id)
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert index_service.embed_selected_payloads == [["hash-a", "hash-b"]]
    assert json.loads(stored_job.summary_json or "{}")["succeeded"] == 2


def test_job_runner_marks_embed_selected_failures(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = FakeIndexService()
    index_service.fail_job_type = "embed_selected"
    job_runner = JobRunner(repository, index_service)

    job = job_runner.enqueue("embed_selected", payload={"content_hashes": ["hash-a"]})
    job_runner.run_next()

    stored_job = repository.get_job(job.id)
    assert stored_job is not None
    assert stored_job.status == "failed"
    assert stored_job.error_text == "embed selected failed"


@pytest.mark.asyncio
async def test_status_service_reads_status_snapshot_and_recent_jobs(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    images_root = tmp_path / "images"
    images_root.mkdir()
    settings = Settings(
        images_root=images_root,
        index_root=tmp_path / "index",
        embedding_provider="jina",
        embedding_model="fake-clip",
        embedding_version="2026-03",
    )
    # Place 3 image files on disk (only 2 are indexed in the metadata DB)
    for name in ("a.jpg", "b.jpg", "c.png"):
        (images_root / name).write_bytes(b"\xff\xd8fake")
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

    snapshot = await status_service.get_index_status()
    jobs = status_service.list_recent_jobs(limit=5)

    assert snapshot.images_on_disk == 3
    assert snapshot.total_images == 2
    assert snapshot.active_images == 1
    assert snapshot.inactive_images == 1
    assert snapshot.vector_entries == 7
    assert snapshot.embedding_provider == "jina"
    assert snapshot.embedding_model == "fake-clip"
    assert snapshot.embedding_version == "2026-03"
    assert snapshot.last_error_summary == "none"
    assert len(jobs) == 1
    assert jobs[0].status == "queued"


def test_background_job_worker_processes_queued_jobs(tmp_path: Path):
    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = FakeIndexService()
    job_runner = JobRunner(repository, index_service)
    worker = BackgroundJobWorker(job_runner, poll_interval_seconds=0.01)

    job = job_runner.enqueue("incremental")
    worker.start()
    try:
        deadline = time.time() + 1.0
        while time.time() < deadline:
            stored_job = repository.get_job(job.id)
            if stored_job is not None and stored_job.status == "succeeded":
                break
            time.sleep(0.02)
    finally:
        worker.stop()

    stored_job = repository.get_job(job.id)
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert index_service.calls == ["incremental"]


def test_background_job_worker_stop_waits_for_running_job(tmp_path: Path):
    class BlockingIndexService(FakeIndexService):
        def __init__(self) -> None:
            super().__init__()
            self.started = Event()
            self.release = Event()

        def run_incremental_update(self) -> IndexingReport:
            self.calls.append("incremental")
            self.started.set()
            self.release.wait(timeout=5.0)
            return IndexingReport(scanned=1, added=1)

    repository = MetadataRepository(tmp_path / "metadata.db")
    repository.initialize_schema()
    index_service = BlockingIndexService()
    job_runner = JobRunner(repository, index_service)
    worker = BackgroundJobWorker(job_runner, poll_interval_seconds=0.01)

    job = job_runner.enqueue("incremental")
    worker.start()
    assert index_service.started.wait(timeout=1.0)

    stop_finished = Event()

    def stop_worker() -> None:
        worker.stop()
        stop_finished.set()

    stop_thread = Thread(target=stop_worker)
    stop_thread.start()
    time.sleep(1.2)
    assert not stop_finished.is_set()

    index_service.release.set()
    stop_thread.join(timeout=1.0)

    stored_job = repository.get_job(job.id)
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stop_finished.is_set()
