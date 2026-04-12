from datetime import UTC, datetime

from fastapi.testclient import TestClient

from image_vector_search.app import create_app
from image_vector_search.config import Settings
from image_vector_search.domain.models import ImageRecord

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_image(
    content_hash: str,
    canonical_path: str,
    *,
    is_active: bool = True,
) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=is_active,
        last_seen_at=NOW,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=NOW,
        updated_at=NOW,
    )


def _insert_image(app_bundle, relative_path: str, *, is_active: bool = True) -> str:
    canonical_path = str(app_bundle.settings.images_root / relative_path)
    content_hash = relative_path.replace("/", "-")
    app_bundle.repository.upsert_image(
        _make_image(content_hash, canonical_path, is_active=is_active)
    )
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


def _canonical_paths(payload: dict) -> list[str]:
    return [image["canonical_path"] for image in payload["images"]]


def test_browse_root_returns_top_level_folders_and_root_images(app_bundle, image_factory):
    top_path = str(image_factory("top.jpg"))
    image_factory("a/1.jpg")
    image_factory("a/b/2.jpg")
    image_factory("a/b/c/3.jpg")
    _insert_image(app_bundle, "top.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == ""
    assert payload["parent"] is None
    assert payload["folders"] == ["a"]
    assert _canonical_paths(payload) == [top_path]
    assert payload["images"][0]["indexed"] is True
    assert payload["next_cursor"] is None


def test_browse_mid_level_returns_direct_subfolders_and_images(app_bundle, image_factory):
    direct_path = str(image_factory("a/1.jpg"))
    image_factory("a/b/2.jpg")
    image_factory("a/b/c/3.jpg")
    image_factory("a/d/4.jpg")
    _insert_image(app_bundle, "a/1.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "a"
    assert payload["parent"] == ""
    assert payload["folders"] == ["a/b", "a/d"]
    assert _canonical_paths(payload) == [direct_path]
    assert payload["images"][0]["indexed"] is True
    assert payload["next_cursor"] is None


def test_browse_leaf_folder_returns_no_subfolders(app_bundle, image_factory):
    leaf_path = str(image_factory("a/b/c/3.jpg"))
    _insert_image(app_bundle, "a/b/c/3.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a/b/c"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["folders"] == []
    assert _canonical_paths(payload) == [leaf_path]


def test_browse_non_existent_folder_returns_empty_result(app_bundle):
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "does/not/exist"})

    assert response.status_code == 200
    assert response.json() == {
        "path": "does/not/exist",
        "parent": "does/not",
        "folders": [],
        "images": [],
        "next_cursor": None,
    }


def test_browse_rejects_path_traversal(app_bundle):
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "../etc"})

    assert response.status_code == 400


def test_browse_rejects_absolute_paths(app_bundle):
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "/etc/passwd"})

    assert response.status_code == 400


def test_browse_normalizes_leading_and_trailing_slashes(app_bundle, image_factory):
    expected_path = str(image_factory("a/1.jpg"))
    _insert_image(app_bundle, "a/1.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "/a/"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "a"
    assert _canonical_paths(payload) == [expected_path]


def test_browse_shows_unindexed_state_for_inactive_or_missing_index(app_bundle, image_factory):
    inactive_path = str(image_factory("a/1.jpg"))
    _insert_image(app_bundle, "a/1.jpg", is_active=False)
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a"})

    assert response.status_code == 200
    payload = response.json()
    assert _canonical_paths(payload) == [inactive_path]
    assert payload["images"][0]["indexed"] is False


def test_browse_does_not_leak_deeper_images_into_parent_view(app_bundle, image_factory):
    image_factory("a/b/2.jpg")
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["folders"] == ["a/b"]
    assert payload["images"] == []


def test_browse_includes_empty_directories_from_filesystem(app_bundle, image_factory):
    image_factory("a/existing.jpg")
    (app_bundle.settings.images_root / "a" / "empty").mkdir(parents=True, exist_ok=True)
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a"})

    assert response.status_code == 200
    assert response.json()["folders"] == ["a/empty"]


def test_browse_returns_unindexed_files_from_filesystem(app_bundle, image_factory):
    file_path = str(image_factory("a/new.jpg"))
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/browse", params={"path": "a"})

    assert response.status_code == 200
    payload = response.json()
    assert _canonical_paths(payload) == [file_path]
    assert payload["images"][0]["indexed"] is False
    assert payload["images"][0]["file_url"].startswith("/api/folders/file?path=")


def test_folder_file_serves_absolute_path_inside_images_root(app_bundle, image_factory):
    file_path = str(image_factory("animals/animals_02.jpg"))
    client = _build_client(app_bundle, authenticated=True)

    response = client.get("/api/folders/file", params={"path": file_path})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/")


def test_browse_requires_authentication(app_bundle):
    client = _build_client(app_bundle, authenticated=False)

    response = client.get("/api/folders/browse")

    assert response.status_code in {401, 307, 302, 303}
