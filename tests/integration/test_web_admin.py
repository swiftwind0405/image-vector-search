from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image as PILImage

from image_search_mcp.app import create_app
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord, ImageRecordWithLabels, IndexStatus, JobRecord, SearchResult


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
            images_on_disk=5,
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

    async def get_index_status(self) -> IndexStatus:
        return self.snapshot

    def list_recent_jobs(self, limit: int = 20) -> list[JobRecord]:
        return self.jobs[:limit]

    def get_job(self, job_id: str) -> JobRecord | None:
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def _make_image_record(self, path: str = "/data/images/red.jpg") -> ImageRecord:
        now = datetime.now(UTC)
        return ImageRecord(
            content_hash="hash-red",
            canonical_path=path,
            file_size=1024,
            mtime=1000.0,
            mime_type="image/jpeg",
            width=12,
            height=8,
            is_active=True,
            last_seen_at=now,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            created_at=now,
            updated_at=now,
        )

    def list_active_images(
        self,
        folder: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
    ):
        return [self._make_image_record()]

    def list_active_images_with_labels(
        self,
        folder: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
    ):
        record = self._make_image_record()
        return [ImageRecordWithLabels(**record.model_dump())]

    def get_image(self, content_hash: str) -> ImageRecord | None:
        if content_hash == "hash-red":
            return self._make_image_record()
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


def test_admin_home_returns_200():
    """API endpoints should work regardless of SPA presence."""
    client = create_test_client()
    response = client.get("/api/status")
    assert response.status_code == 200


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


def test_list_images_api():
    client = create_test_client()
    response = client.get("/api/images")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_images_returns_tags_and_categories():
    client = create_test_client()
    response = client.get("/api/images")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert "tags" in body[0]
    assert "categories" in body[0]
    assert isinstance(body[0]["tags"], list)
    assert isinstance(body[0]["categories"], list)


def test_thumbnail_missing_record_returns_404():
    client = create_test_client()
    response = client.get("/api/images/nonexistent-hash/thumbnail")
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"


def test_thumbnail_size_out_of_bounds_returns_422():
    client = create_test_client()
    # too small
    response = client.get("/api/images/hash-red/thumbnail?size=10")
    assert response.status_code == 422
    # too large
    response = client.get("/api/images/hash-red/thumbnail?size=600")
    assert response.status_code == 422


def test_thumbnail_file_missing_on_disk_returns_404():
    """hash-red record exists in DB but canonical_path is /data/images/red.jpg (doesn't exist on disk)."""
    client = create_test_client()
    response = client.get("/api/images/hash-red/thumbnail")
    assert response.status_code == 404
    assert response.json()["detail"] == "not found"


def test_thumbnail_returns_jpeg(tmp_path: Path):
    """Integration test: real JPEG on disk returns 200 image/jpeg."""
    # Create a real image file
    img_path = tmp_path / "test.jpg"
    PILImage.new("RGB", (200, 150), color=(100, 150, 200)).save(img_path)

    status_service = FakeStatusService()
    # Override get_image to return real path
    real_record = status_service._make_image_record(path=str(img_path))
    status_service.get_image = lambda h: real_record if h == "hash-red" else None  # type: ignore[assignment]

    app = create_app(
        settings=Settings(),
        search_service=FakeSearchService(),
        status_service=status_service,
        job_runner=FakeJobRunner(status_service),
    )
    client = TestClient(app)

    response = client.get("/api/images/hash-red/thumbnail?size=120")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "max-age=86400"
    # Verify it's valid JPEG by opening it
    from io import BytesIO
    with PILImage.open(BytesIO(response.content)) as img:
        assert img.format == "JPEG"
        assert img.width <= 120
        assert img.height <= 120
