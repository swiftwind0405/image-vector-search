# Task 005: Settings API Endpoints — Tests

**type:** test  
**depends-on:** ["004"]

## Goal

Write unit tests for `GET /api/settings/embedding` and `PUT /api/settings/embedding` endpoints. Tests use FastAPI's `TestClient` with mocked `RuntimeServices` and `MetadataRepository`.

## BDD Scenarios

```gherkin
Scenario 1: View current configuration (masked)
  Given embedding provider "jina" and a Jina API key are configured in DB
  When GET /api/settings/embedding is called
  Then response is 200 with {provider: "jina", jina_api_key_configured: true, google_api_key_configured: false}
  And no API key value appears in the response body

Scenario 2: Save new provider and API key (happy path)
  Given valid credentials are submitted
  When PUT /api/settings/embedding is called with {provider: "gemini", google_api_key: "key123", jina_api_key: null}
  Then repository.set_embedding_config is called with provider="gemini", google_api_key="key123"
  And runtime_services.reload_embedding_client() is awaited
  And response is 200 with updated config status

Scenario 3b: Change provider when target key is missing
  Given no Google API key in DB or env vars
  When PUT /api/settings/embedding is called with {provider: "gemini", google_api_key: null}
  Then response is 422
  With detail "No API key configured for provider 'gemini'"
  And set_embedding_config is NOT called

Scenario 4: Save with invalid provider value
  When PUT /api/settings/embedding is called with {provider: "openai"}
  Then response is 422
  And detail says "provider must be 'jina' or 'gemini'"
  And no DB writes occur

Scenario 5: Reload fails after successful DB write
  Given DB write succeeds
  But reload_embedding_client() raises RuntimeError("timeout")
  When PUT /api/settings/embedding is called
  Then response is 500
  And detail contains "Settings saved but embedding reload failed: timeout"

Scenario 6: No configuration at startup
  Given no config in DB and no env vars
  When GET /api/settings/embedding is called
  Then response is 200 with {provider: "", jina_api_key_configured: false, google_api_key_configured: false}
```

## Files to Create

- `tests/unit/test_settings_routes.py`

## Test Cases

1. `test_get_returns_masked_configured_status` — mock repo returning jina_api_key, assert response has `jina_api_key_configured: true` and no key value
2. `test_get_returns_empty_when_no_config` — mock repo returning all None + empty settings, assert response has all false flags
3. `test_put_valid_saves_and_reloads` — mock repo + reload, call PUT, assert both called
4. `test_put_invalid_provider_returns_422` — no mocks needed, just call with "openai"
5. `test_put_missing_target_key_returns_422` — mock repo returns no google key, settings has no google key, PUT with provider=gemini + null key
6. `test_put_reload_failure_returns_500` — mock reload to raise, assert 500 with detail, assert DB write still happened

## Test Setup Pattern

```python
# Use FastAPI TestClient with create_settings_router injected with mocks
from unittest.mock import AsyncMock, MagicMock
mock_repo = MagicMock()
mock_runtime = MagicMock()
mock_runtime.reload_embedding_client = AsyncMock()
mock_settings = Settings(...)
router = create_settings_router(runtime_services=mock_runtime, repository=mock_repo, settings=mock_settings)
```

## Verification

```bash
pytest tests/unit/test_settings_routes.py -v
```

All 6 tests must fail (Red) before implementation.
