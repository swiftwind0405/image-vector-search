# Task 006: Settings API Endpoints — Implementation

**type:** impl  
**depends-on:** ["005"]

## Goal

Implement `GET /api/settings/embedding` and `PUT /api/settings/embedding` endpoints. Wire them into `app.py`. No DB schema changes needed.

## BDD Scenarios

```gherkin
Scenario 2: Save new provider and API key (happy path)
  When PUT /api/settings/embedding called with valid provider+key
  Then DB saved, client reloaded, 200 returned

Scenario 3b: Change provider when target key is missing
  When PUT called with provider that has no key configured
  Then 422 returned, no DB write, no reload

Scenario 5: Reload fails after successful DB write
  When DB write succeeds but reload raises
  Then 500 returned with detail, DB write is persisted
```

## Files to Modify

- `src/image_vector_search/frontend/routes.py`
- `src/image_vector_search/app.py`

## What to Implement

### In `web/routes.py` — add `create_settings_router`

**Request model** `EmbeddingSettingsRequest`:
- `provider: str`
- `jina_api_key: str | None = None`
- `google_api_key: str | None = None`

**`GET /api/settings/embedding`**:
1. Call `repository.get_embedding_config()`
2. Resolve `provider` (DB → `settings.embedding_provider` → `""`)
3. Resolve `jina_api_key_configured`: `bool(db_cfg["jina_api_key"] or settings.jina_api_key)`
4. Resolve `google_api_key_configured`: `bool(db_cfg["google_api_key"] or settings.google_api_key)`
5. Return JSON — never include plaintext keys

**`PUT /api/settings/embedding`**:
1. Validate `provider in {"jina", "gemini"}` → 422 if not
2. Read `db_cfg = repository.get_embedding_config()`
3. Compute `effective_key` for the target provider (new value → DB → settings fallback)
4. If `effective_key` is empty → raise 422 `"No API key configured for provider '{provider}'"`
5. Call `repository.set_embedding_config(provider=payload.provider, jina_api_key=payload.jina_api_key, google_api_key=payload.google_api_key)`
6. Try `await runtime_services.reload_embedding_client()`; on exception → raise HTTPException 500 with detail `"Settings saved but embedding reload failed: {exc}"`
7. Return updated config (same shape as GET)

**Function signature**:
```python
def create_settings_router(
    *,
    runtime_services: RuntimeServices,
    repository: MetadataRepository,
    settings: Settings,
) -> APIRouter:
```

### In `app.py` — wire settings router

When `runtime_services` is available (i.e., not using injected test services):
- Extract `repository` from `runtime_services.repository`
- Call `create_settings_router(runtime_services=runtime_services, repository=repository, settings=app_settings)`
- Include the router in the app

## Verification

```bash
pytest tests/unit/test_settings_routes.py -v
pytest tests/unit/ -v  # no regressions
```

All 6 settings tests must pass (Green).
