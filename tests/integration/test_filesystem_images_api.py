from datetime import UTC, datetime

from fastapi.testclient import TestClient

from image_vector_search.app import create_app
from image_vector_search.domain.models import ImageRecord


def _insert_image(app_bundle, relative_path: str) -> str:
    canonical_path = str(app_bundle.settings.images_root / relative_path)
    content_hash = relative_path.replace("/", "-")
    now = datetime(2026, 1, 1, tzinfo=UTC)
    image = ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=True,
        last_seen_at=now,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=now,
        updated_at=now,
    )
    app_bundle.repository.upsert_image(image)
    return canonical_path


def _build_client(app_bundle, *, authenticated: bool) -> TestClient:
    settings = app_bundle.settings.model_copy(
        update={
            "admin_username": "admin",
            "admin_password": "secret",
            "admin_session_secret": "test-secret",
        }
    )
    app = create_app(
        settings=settings,
        search_service=app_bundle.search_service,
        status_service=app_bundle.status_service,
        job_runner=app_bundle.job_runner,
    )
    app.router.routes = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) != "/{path:path}"
    ]
    client = TestClient(app)
    if authenticated:
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "secret"},
        )
        assert response.status_code == 200
    return client


def test_filesystem_images_returns_all_supported_files_recursively(app_bundle, image_factory):
    image_factory("top.jpg")
    image_factory("animals/cat.jpg")
    image_factory("animals/nested/bird.png")
    (app_bundle.settings.images_root / "notes.txt").write_text("ignore me", encoding="utf-8")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/images/filesystem")

    assert response.status_code == 200
    payload = response.json()
    paths = [item["canonical_path"] for item in payload["items"]]
    assert paths == sorted(
        [
            str(app_bundle.settings.images_root / "animals" / "cat.jpg"),
            str(app_bundle.settings.images_root / "animals" / "nested" / "bird.png"),
            str(app_bundle.settings.images_root / "top.jpg"),
        ]
    )
    assert all("file_url" in item for item in payload["items"])


def test_filesystem_images_marks_indexed_and_unindexed_files(app_bundle, image_factory):
    indexed_path = str(image_factory("indexed.jpg"))
    unindexed_path = str(image_factory("unindexed.jpg"))

    _insert_image(app_bundle, "indexed.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/images/filesystem")

    assert response.status_code == 200
    items = {item["canonical_path"]: item for item in response.json()["items"]}
    assert items[indexed_path]["indexed"] is True
    assert items[unindexed_path]["indexed"] is False


def test_filesystem_images_requires_authentication(app_bundle):
    client = _build_client(app_bundle, authenticated=False)

    response = client.get("/api/images/filesystem")

    assert response.status_code == 401
