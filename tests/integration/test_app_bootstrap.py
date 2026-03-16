from datetime import UTC, datetime

from fastapi.testclient import TestClient

import image_search_mcp.app as app_module
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import IndexStatus, JobRecord, SearchResult


class FakeSearchService:
    async def search_images(self, **kwargs):
        return [
            SearchResult(
                content_hash="hash-red",
                path="/data/images/red.jpg",
                score=0.9,
                width=12,
                height=8,
                mime_type="image/jpeg",
            )
        ]

    async def search_similar(self, **kwargs):
        return []


class FakeStatusService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.snapshot = IndexStatus(
            images_on_disk=2,
            total_images=1,
            active_images=1,
            inactive_images=0,
            vector_entries=1,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            last_incremental_update_at=now,
            last_full_rebuild_at=None,
            last_error_summary=None,
        )
        self.jobs = [
            JobRecord(
                id="job-1",
                job_type="incremental",
                status="queued",
                requested_at=now,
            )
        ]

    def get_index_status(self):
        return self.snapshot

    def list_recent_jobs(self, limit: int = 20):
        return self.jobs[:limit]

    def get_job(self, job_id: str):
        return self.jobs[0] if self.jobs and self.jobs[0].id == job_id else None


class FakeJobRunner:
    def enqueue(self, job_type: str):
        return JobRecord(
            id="job-2",
            job_type=job_type,
            status="queued",
            requested_at=datetime.now(UTC),
        )


class FakeBackgroundWorker:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class FakeRuntimeServices:
    def __init__(self) -> None:
        self.search_service = FakeSearchService()
        self.status_service = FakeStatusService()
        self.job_runner = FakeJobRunner()
        self.background_worker = FakeBackgroundWorker()
        self.closed = 0

    async def aclose(self) -> None:
        self.closed += 1


def test_create_app_bootstraps_runtime_services(monkeypatch, tmp_path):
    runtime_services = FakeRuntimeServices()
    monkeypatch.setattr(
        app_module,
        "build_runtime_services",
        lambda settings: runtime_services,
    )

    app = app_module.create_app(
        settings=Settings(images_root=tmp_path / "images", index_root=tmp_path / "index")
    )

    with TestClient(app) as client:
        assert runtime_services.background_worker.started == 1
        assert client.get("/api/status").status_code == 200
        assert client.post("/api/debug/search/text", json={"query": "red flower"}).status_code == 200

    assert runtime_services.background_worker.stopped == 1
    assert runtime_services.closed == 1
