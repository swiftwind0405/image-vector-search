from unittest.mock import AsyncMock

import pytest

from image_search_mcp.config import Settings
from image_search_mcp import runtime as runtime_module
from image_search_mcp.runtime import build_runtime_services


class _FakeEmbeddingClient:
    def __init__(self, name: str) -> None:
        self.name = name
        self.aclose = AsyncMock()


class _FakeVectorIndex:
    def __init__(self, db_path, collection_name) -> None:
        self.db_path = db_path
        self.collection_name = collection_name

    def close(self) -> None:
        return None


def _build_settings(tmp_path, **overrides) -> Settings:
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()
    return Settings(images_root=images_root, index_root=index_root, **overrides)


@pytest.fixture
def patch_runtime_dependencies(monkeypatch):
    monkeypatch.setattr(runtime_module, "MilvusLiteIndex", _FakeVectorIndex)


@pytest.mark.asyncio
async def test_reload_swaps_all_three_references(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(runtime_module, "MilvusLiteIndex", _FakeVectorIndex)
    initial_client = _FakeEmbeddingClient("initial")
    monkeypatch.setattr(runtime_module, "_build_embedding_client", lambda _settings: initial_client)
    runtime_services = build_runtime_services(settings)
    old_client = _FakeEmbeddingClient("old")
    new_client = _FakeEmbeddingClient("new")
    runtime_services.embedding_client = old_client
    runtime_services.search_service.embedding_client = old_client
    runtime_services.job_runner.index_service.embedding_client = old_client
    runtime_services.search_service.repository.set_embedding_config(
        provider="jina",
        jina_api_key="new-secret",
    )
    monkeypatch.setattr(
        runtime_module,
        "_build_embedding_client_from",
        lambda *_args, **_kwargs: new_client,
        raising=False,
    )

    await runtime_services.reload_embedding_client()

    assert runtime_services.embedding_client is new_client
    assert runtime_services.search_service.embedding_client is new_client
    assert runtime_services.job_runner.index_service.embedding_client is new_client


@pytest.mark.asyncio
async def test_reload_calls_aclose_on_old_client(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(runtime_module, "MilvusLiteIndex", _FakeVectorIndex)
    initial_client = _FakeEmbeddingClient("initial")
    monkeypatch.setattr(runtime_module, "_build_embedding_client", lambda _settings: initial_client)
    runtime_services = build_runtime_services(settings)
    old_client = _FakeEmbeddingClient("old")
    new_client = _FakeEmbeddingClient("new")
    runtime_services.embedding_client = old_client
    runtime_services.search_service.embedding_client = old_client
    runtime_services.job_runner.index_service.embedding_client = old_client
    runtime_services.search_service.repository.set_embedding_config(
        provider="jina",
        jina_api_key="new-secret",
    )
    monkeypatch.setattr(
        runtime_module,
        "_build_embedding_client_from",
        lambda *_args, **_kwargs: new_client,
        raising=False,
    )

    await runtime_services.reload_embedding_client()

    old_client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_reload_does_not_swap_on_error(tmp_path, monkeypatch):
    monkeypatch.delenv("IMAGE_SEARCH_JINA_API_KEY", raising=False)
    monkeypatch.delenv("IMAGE_SEARCH_GOOGLE_API_KEY", raising=False)
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(runtime_module, "MilvusLiteIndex", _FakeVectorIndex)
    initial_client = _FakeEmbeddingClient("initial")
    monkeypatch.setattr(runtime_module, "_build_embedding_client", lambda _settings: initial_client)
    runtime_services = build_runtime_services(settings)
    old_client = _FakeEmbeddingClient("old")
    runtime_services.embedding_client = old_client
    runtime_services.search_service.embedding_client = old_client
    runtime_services.job_runner.index_service.embedding_client = old_client
    runtime_services.search_service.repository.set_embedding_config(provider="jina")

    with pytest.raises(ValueError):
        await runtime_services.reload_embedding_client()

    assert runtime_services.embedding_client is old_client
    assert runtime_services.search_service.embedding_client is old_client
    assert runtime_services.job_runner.index_service.embedding_client is old_client


def test_startup_no_config_does_not_crash(tmp_path, monkeypatch, patch_runtime_dependencies):
    monkeypatch.delenv("IMAGE_SEARCH_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("IMAGE_SEARCH_JINA_API_KEY", raising=False)
    monkeypatch.delenv("IMAGE_SEARCH_GOOGLE_API_KEY", raising=False)

    runtime_services = build_runtime_services(_build_settings(tmp_path))

    assert runtime_services.embedding_client is None


def test_startup_env_var_fallback(tmp_path, monkeypatch, patch_runtime_dependencies):
    monkeypatch.setenv("IMAGE_SEARCH_EMBEDDING_PROVIDER", "jina")
    monkeypatch.setenv("IMAGE_SEARCH_JINA_API_KEY", "env-secret")
    captured = {}

    def _build_embedding_client_from(provider, api_key, settings):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["settings"] = settings
        return _FakeEmbeddingClient("env")

    monkeypatch.setattr(
        runtime_module,
        "_build_embedding_client_from",
        _build_embedding_client_from,
        raising=False,
    )
    monkeypatch.setattr(
        runtime_module,
        "_build_embedding_client",
        lambda _settings: pytest.fail("build_runtime_services should resolve config via _build_embedding_client_from"),
    )

    runtime_services = build_runtime_services(_build_settings(tmp_path))

    assert runtime_services.embedding_client.name == "env"
    assert captured["provider"] == "jina"
    assert captured["api_key"] == "env-secret"
