from datetime import UTC, datetime

from fastapi.testclient import TestClient

from image_search_mcp.app import create_app
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import IndexStatus, JobRecord, SearchResult


class FakeStatusService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.jobs = [
            JobRecord(
                id="job-1",
                job_type="incremental",
                status="queued",
                requested_at=now,
            )
        ]
        self.snapshot = IndexStatus(
            total_images=3,
            active_images=2,
            inactive_images=1,
            vector_entries=3,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            last_incremental_update_at=now,
            last_full_rebuild_at=None,
            last_error_summary=None,
        )

    def get_index_status(self) -> IndexStatus:
        return self.snapshot

    def list_recent_jobs(self, limit: int = 20) -> list[JobRecord]:
        return self.jobs[:limit]

    def get_job(self, job_id: str) -> JobRecord | None:
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None


class FakeJobRunner:
    def __init__(self, status_service: FakeStatusService) -> None:
        self.status_service = status_service
        self.enqueued: list[str] = []

    def enqueue(self, job_type: str) -> JobRecord:
        now = datetime.now(UTC)
        job = JobRecord(
            id=f"job-{len(self.enqueued) + 2}",
            job_type=job_type,
            status="queued",
            requested_at=now,
        )
        self.enqueued.append(job_type)
        self.status_service.jobs.insert(0, job)
        return job


class FakeSearchService:
    async def search_images(self, **kwargs) -> list[SearchResult]:
        return [
            SearchResult(
                content_hash="hash-red",
                path="/data/images/red.jpg",
                score=0.91,
                width=12,
                height=8,
                mime_type="image/jpeg",
            )
        ]

    async def search_similar(self, **kwargs) -> list[SearchResult]:
        return [
            SearchResult(
                content_hash="hash-blue",
                path="/data/images/blue.jpg",
                score=0.88,
                width=12,
                height=8,
                mime_type="image/jpeg",
            )
        ]


def create_test_client() -> TestClient:
    status_service = FakeStatusService()
    app = create_app(
        settings=Settings(),
        search_service=FakeSearchService(),
        status_service=status_service,
        job_runner=FakeJobRunner(status_service),
    )
    return TestClient(app)


def test_admin_home_shows_status_and_actions():
    client = create_test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert "Incremental Update" in response.text
    assert "Full Rebuild" in response.text
    assert "Debug Search" in response.text


def test_status_api_returns_snapshot():
    client = create_test_client()

    response = client.get("/api/status")

    assert response.status_code == 200
    body = response.json()
    assert body["active_images"] == 2
    assert body["vector_entries"] == 3
    assert body["embedding_model"] == "fake-clip"


def test_job_creation_api_enqueues_incremental_update():
    client = create_test_client()

    response = client.post("/api/jobs/incremental")

    assert response.status_code == 202
    assert response.json()["job_type"] == "incremental"


def test_debug_text_search_returns_results():
    client = create_test_client()

    response = client.post(
        "/api/debug/search/text",
        json={"query": "red flower", "top_k": 1},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["content_hash"] == "hash-red"
