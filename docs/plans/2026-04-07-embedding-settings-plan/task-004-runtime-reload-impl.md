# Task 004: RuntimeServices Hot-Reload — Implementation

**type:** impl  
**depends-on:** ["003"]

## Goal

Modify `src/image_search_mcp/runtime.py` to:
1. Add `index_service`, `repository`, and `settings` fields to `RuntimeServices`
2. Add `async reload_embedding_client()` method to `RuntimeServices`
3. Modify `build_runtime_services()` to resolve embedding config from DB first, then env var fallback, without crashing when neither is set

## BDD Scenarios

```gherkin
Scenario: reload_embedding_client updates all service references
  Given RuntimeServices is built with an initial embedding client
  When reload_embedding_client() is called after new config is saved to DB
  Then search_service.embedding_client, index_service.embedding_client,
       and RuntimeServices.embedding_client are all the new instance
  And old client's aclose() was called

Scenario: Startup with no config (fresh install)
  Given no config.* keys in system_state and no env vars
  When build_runtime_services(settings) is called
  Then it completes without raising and embedding_client is None

Scenario: Startup with env vars only (existing deployment)
  Given env vars set, no DB config
  When build_runtime_services(settings) is called
  Then embedding_client is built from env vars
```

## Files to Modify

- `src/image_search_mcp/runtime.py`

## What to Implement

### 1. Update `RuntimeServices` dataclass

Add fields (after existing fields):
- `index_service: IndexService`
- `repository: MetadataRepository`
- `settings: Settings`

Update `aclose()` to not reference embedding_client directly if it might be None.

### 2. Add `_build_embedding_client_from(provider, api_key, settings)` free function

Extract provider-specific client construction into a standalone function that takes explicit `provider` and `api_key` strings (rather than reading from `settings`). Returns `EmbeddingClient | None` — returns `None` if provider or api_key is empty.

This replaces the current `_build_embedding_client(settings)` or becomes a complementary helper.

### 3. Add `async reload_embedding_client()` method to `RuntimeServices`

Steps:
1. Read `db_config = self.repository.get_embedding_config()`
2. Resolve `provider`: DB value → `self.settings.embedding_provider` fallback
3. Resolve `api_key`: DB value for that provider → env var fallback
4. If provider or api_key empty: raise `ValueError("Embedding not configured")`
5. `new_client = _build_embedding_client_from(provider, api_key, self.settings)`
6. `old_client = self.embedding_client`
7. Swap: `self.embedding_client = new_client`, `self.search_service.embedding_client = new_client`, `self.index_service.embedding_client = new_client`
8. `await old_client.aclose()` (swallow exceptions)

### 4. Modify `build_runtime_services(settings)`

After `repository.initialize_schema()`:
1. Call `repository.get_embedding_config()`
2. Resolve provider and api_key (DB → env var fallback)
3. If both empty: `embedding_client = None`
4. Otherwise: call `_build_embedding_client_from(provider, api_key, settings)`
5. Pass `index_service`, `repository`, `settings` when constructing `RuntimeServices`

### 5. Guard IndexService/SearchService for None client

IndexService and SearchService should raise a clear error on first use if `embedding_client is None`. No change needed if they already raise `AttributeError` — but if needed, add an explicit check in their embed methods.

## Verification

```bash
pytest tests/unit/test_runtime_reload.py -v
pytest tests/unit/ -v  # ensure no regressions
```

All tests must pass (Green).
