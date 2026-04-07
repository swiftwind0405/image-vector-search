from image_vector_search.repositories.sqlite import MetadataRepository


def _build_repository(tmp_path):
    repository = MetadataRepository(tmp_path / "metadata.sqlite3")
    repository.initialize_schema()
    return repository


def test_get_embedding_config_returns_none_when_empty(tmp_path):
    repository = _build_repository(tmp_path)

    assert repository.get_embedding_config() == {
        "provider": None,
        "jina_api_key": None,
        "google_api_key": None,
    }


def test_get_embedding_config_returns_stored_values(tmp_path):
    repository = _build_repository(tmp_path)
    repository.set_system_state("config.embedding_provider", "gemini")
    repository.set_system_state("config.jina_api_key", "jina-secret")
    repository.set_system_state("config.google_api_key", "google-secret")

    assert repository.get_embedding_config() == {
        "provider": "gemini",
        "jina_api_key": "jina-secret",
        "google_api_key": "google-secret",
    }


def test_set_embedding_config_writes_only_specified_keys(tmp_path):
    repository = _build_repository(tmp_path)

    repository.set_embedding_config(provider="jina")

    assert repository.get_system_state("config.embedding_provider") == "jina"
    assert repository.get_system_state("config.jina_api_key") is None
    assert repository.get_system_state("config.google_api_key") is None


def test_set_embedding_config_null_does_not_overwrite(tmp_path):
    repository = _build_repository(tmp_path)
    repository.set_system_state("config.jina_api_key", "existing-key")

    repository.set_embedding_config(jina_api_key=None)

    assert repository.get_system_state("config.jina_api_key") == "existing-key"


def test_set_embedding_config_overwrites_when_value_given(tmp_path):
    repository = _build_repository(tmp_path)
    repository.set_system_state("config.jina_api_key", "old-key")

    repository.set_embedding_config(jina_api_key="new-key")

    assert repository.get_system_state("config.jina_api_key") == "new-key"
