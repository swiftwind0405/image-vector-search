from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from image_vector_search.config import Settings
from image_vector_search.repositories.sqlite import MetadataRepository


def _build_repository(tmp_path):
    repository = MetadataRepository(tmp_path / "metadata.sqlite3")
    repository.initialize_schema()
    return repository


def _build_client(tmp_path, *, settings: Settings | None = None, repository: MetadataRepository | None = None):
    from image_vector_search.api.admin_settings_routes import create_admin_settings_router

    repository = repository or _build_repository(tmp_path)
    settings = settings or Settings(
        images_root=tmp_path / "images",
        index_root=tmp_path / "index",
        jina_api_key="",
        google_api_key="",
    )
    runtime_services = SimpleNamespace(reload_embedding_client=AsyncMock())
    status_service = MagicMock()
    status_service.get_excluded_folders.return_value = []
    status_service.list_disk_folders.return_value = []

    app = FastAPI()
    app.include_router(
        create_admin_settings_router(
            runtime_services=runtime_services,
            repository=repository,
            settings=settings,
            status_service=status_service,
        )
    )
    return TestClient(app), repository, runtime_services, status_service


def test_get_settings_returns_masked_shape_without_plaintext_keys(tmp_path):
    client, repository, _runtime_services, _status_service = _build_client(tmp_path)
    repository.set_embedding_config(provider="jina", jina_api_key="secret-jina")

    response = client.get("/api/settings/embedding")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "jina",
        "jina_api_key_configured": True,
        "google_api_key_configured": False,
        "using_environment_fallback": False,
    }
    assert "secret-jina" not in response.text


def test_put_settings_saves_and_reloads_client(tmp_path):
    client, repository, runtime_services, _status_service = _build_client(tmp_path)

    response = client.put(
        "/api/settings/embedding",
        json={
            "provider": "gemini",
            "jina_api_key": None,
            "google_api_key": "key123",
        },
    )

    assert response.status_code == 200
    assert repository.get_embedding_config() == {
        "provider": "gemini",
        "jina_api_key": None,
        "google_api_key": "key123",
    }
    runtime_services.reload_embedding_client.assert_awaited_once()
    assert response.json() == {
        "provider": "gemini",
        "jina_api_key_configured": False,
        "google_api_key_configured": True,
        "using_environment_fallback": False,
    }


def test_put_settings_uses_existing_db_key_for_target_provider(tmp_path):
    client, repository, runtime_services, _status_service = _build_client(tmp_path)
    repository.set_embedding_config(google_api_key="persisted-google")

    response = client.put(
        "/api/settings/embedding",
        json={
            "provider": "gemini",
            "jina_api_key": None,
            "google_api_key": None,
        },
    )

    assert response.status_code == 200
    runtime_services.reload_embedding_client.assert_awaited_once()
    assert repository.get_embedding_config()["provider"] == "gemini"
    assert repository.get_embedding_config()["google_api_key"] == "persisted-google"


def test_put_settings_uses_env_fallback_when_target_key_not_in_db(tmp_path):
    settings = Settings(
        images_root=tmp_path / "images",
        index_root=tmp_path / "index",
        embedding_provider="jina",
        jina_api_key="env-secret",
    )
    client, repository, runtime_services, _status_service = _build_client(tmp_path, settings=settings)

    response = client.put(
        "/api/settings/embedding",
        json={
            "provider": "jina",
            "jina_api_key": None,
            "google_api_key": None,
        },
    )

    assert response.status_code == 200
    runtime_services.reload_embedding_client.assert_awaited_once()
    assert response.json()["using_environment_fallback"] is True
    assert repository.get_embedding_config()["provider"] == "jina"


def test_put_settings_rejects_missing_effective_key(tmp_path):
    client, _repository, runtime_services, _status_service = _build_client(tmp_path)

    response = client.put(
        "/api/settings/embedding",
        json={
            "provider": "gemini",
            "jina_api_key": None,
            "google_api_key": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "No API key configured for provider 'gemini'"
    runtime_services.reload_embedding_client.assert_not_awaited()


def test_put_settings_returns_500_when_reload_fails(tmp_path):
    client, repository, runtime_services, _status_service = _build_client(tmp_path)
    runtime_services.reload_embedding_client.side_effect = RuntimeError("timeout")

    response = client.put(
        "/api/settings/embedding",
        json={
            "provider": "jina",
            "jina_api_key": "new-secret",
            "google_api_key": None,
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Settings saved but embedding reload failed: timeout"
    assert repository.get_embedding_config()["jina_api_key"] == "new-secret"


def test_get_folder_settings_returns_disk_folders_and_excluded(tmp_path):
    client, _repository, _runtime_services, status_service = _build_client(tmp_path)
    status_service.list_disk_folders.return_value = ["a", "a/b", "c"]
    status_service.get_excluded_folders.return_value = ["a/b"]

    response = client.get("/api/settings/folders")

    assert response.status_code == 200
    assert response.json() == {"folders": ["a", "a/b", "c"], "excluded": ["a/b"]}


def test_put_excluded_folders_persists_and_returns_refreshed_state(tmp_path):
    client, _repository, _runtime_services, status_service = _build_client(tmp_path)
    status_service.list_disk_folders.return_value = ["keep", "drop"]
    # Simulate persistence: after set_excluded_folders is called,
    # get_excluded_folders reflects the new value.
    current: list[str] = []

    def _set(folders):
        current[:] = list(folders)

    status_service.set_excluded_folders.side_effect = _set
    status_service.get_excluded_folders.side_effect = lambda: list(current)

    response = client.put(
        "/api/settings/excluded-folders",
        json={"excluded": ["drop"]},
    )

    assert response.status_code == 200
    status_service.set_excluded_folders.assert_called_once_with(["drop"])
    assert response.json() == {"folders": ["keep", "drop"], "excluded": ["drop"]}
