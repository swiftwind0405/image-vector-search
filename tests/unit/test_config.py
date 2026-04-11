import os
from pathlib import Path

import pytest

from image_vector_search.config import Settings


def test_settings_defaults(monkeypatch):
    # Clear environment variables that would override defaults
    for key in list(os.environ.keys()):
        if key.startswith("IMAGE_SEARCH_"):
            monkeypatch.delenv(key, raising=False)
    settings = Settings()
    assert settings.images_root == Path("/data/images")
    assert settings.index_root == Path("/data/index")
    assert settings.default_top_k == 5
    assert settings.max_top_k == 50
    assert settings.embedding_provider == "jina"
    assert settings.max_embedding_file_size_mb == 2


def test_settings_load_gemini_specific_values(monkeypatch):
    monkeypatch.setenv("IMAGE_SEARCH_EMBEDDING_PROVIDER", "gemini")
    monkeypatch.setenv("IMAGE_SEARCH_GOOGLE_API_KEY", "google-secret")
    monkeypatch.setenv("IMAGE_SEARCH_GEMINI_BASE_URL", "https://example.test/v1beta")
    monkeypatch.setenv("IMAGE_SEARCH_EMBEDDING_OUTPUT_DIMENSIONALITY", "512")

    settings = Settings()

    assert settings.embedding_provider == "gemini"
    assert settings.google_api_key == "google-secret"
    assert settings.gemini_base_url == "https://example.test/v1beta"
    assert settings.embedding_output_dimensionality == 512


def test_settings_normalize_embedding_provider():
    settings = Settings(embedding_provider="  GEMINI  ")
    assert settings.embedding_provider == "gemini"


def test_settings_reject_unsupported_embedding_provider():
    with pytest.raises(ValueError, match="embedding_provider"):
        Settings(embedding_provider="unsupported")


def test_settings_gemini_provider_applies_model_defaults():
    settings = Settings(embedding_provider="gemini")
    assert settings.embedding_model == "gemini-embedding-2-preview"
    assert settings.embedding_version == "preview"


def test_settings_gemini_provider_preserves_explicit_model():
    settings = Settings(
        embedding_provider="gemini",
        embedding_model="custom-model",
        embedding_version="v3",
    )
    assert settings.embedding_model == "custom-model"
    assert settings.embedding_version == "v3"


def test_build_embedding_key_handles_none_version():
    from image_vector_search.adapters.embedding.base import build_embedding_key

    assert build_embedding_key("gemini", "model", None) == "gemini:model:default"
    assert build_embedding_key("jina", "clip", "v2") == "jina:clip:v2"


def test_settings_allow_embedding_size_override(monkeypatch):
    monkeypatch.setenv("IMAGE_SEARCH_MAX_EMBEDDING_FILE_SIZE_MB", "10")

    settings = Settings()

    assert settings.max_embedding_file_size_mb == 10


def test_settings_allow_disabling_embedding_size_limit():
    settings = Settings(max_embedding_file_size_mb=0)

    assert settings.max_embedding_file_size_mb == 0
