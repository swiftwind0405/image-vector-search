# Task 003: RuntimeServices Hot-Reload — Tests

**type:** test  
**depends-on:** ["002"]

## Goal

Write unit tests covering: (a) `RuntimeServices.reload_embedding_client()` swaps client references on all three service objects; (b) `build_runtime_services()` resolves embedding config from DB first, falls back to env vars, and does not crash when neither is set.

## BDD Scenarios

```gherkin
Scenario: reload_embedding_client updates all service references
  Given RuntimeServices is built with an initial embedding client
  When reload_embedding_client() is called after new config is saved to DB
  Then search_service.embedding_client is the new client instance
  And index_service.embedding_client is the new client instance
  And RuntimeServices.embedding_client is the new client instance
  And the old client's aclose() was called

Scenario: reload with missing API key raises ValueError
  Given system_state has provider="jina" but no jina_api_key
  And no JINA_API_KEY env var is set
  When reload_embedding_client() is called
  Then it raises ValueError
  And the existing embedding_client is NOT replaced

Scenario: Startup with no config (fresh install)
  Given no config.* keys in system_state
  And no embedding env vars set
  When build_runtime_services(settings) is called
  Then it completes without raising
  And RuntimeServices.embedding_client is None

Scenario: Startup with env vars only (existing deployment)
  Given IMAGE_SEARCH_EMBEDDING_PROVIDER=jina and IMAGE_SEARCH_JINA_API_KEY are set
  And no config.* keys in system_state
  When build_runtime_services(settings) is called
  Then RuntimeServices.embedding_client is a JinaEmbeddingClient
```

## Files to Create

- `tests/unit/test_runtime_reload.py`

## Test Cases

1. `test_reload_swaps_all_three_references` — build RuntimeServices with a mock client, save new config to DB, call reload, assert all three `.embedding_client` references changed
2. `test_reload_calls_aclose_on_old_client` — mock old client, reload, assert `aclose()` was awaited
3. `test_reload_does_not_swap_on_error` — save provider with no API key, call reload, assert original client unchanged
4. `test_startup_no_config_does_not_crash` — build_runtime_services with empty DB and no env vars, assert completes and `.embedding_client is None`
5. `test_startup_env_var_fallback` — monkeypatch env vars, empty DB, build_runtime_services, assert client type is JinaEmbeddingClient

## Notes

- Use `unittest.mock` for embedding clients; patch `_build_embedding_client_from` or mock the Jina/Gemini clients
- Use `respx` or mock for any HTTP calls made during client construction
- Use a temp directory for the SQLite DB (matching existing test patterns in `tests/unit/`)

## Verification

```bash
pytest tests/unit/test_runtime_reload.py -v
```

All 5 tests must fail (Red) before implementation.
