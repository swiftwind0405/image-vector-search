# Architecture: Embedding Settings Admin UI

## Current State

### Embedding Config Flow (env vars → services)

```
IMAGE_SEARCH_EMBEDDING_PROVIDER
IMAGE_SEARCH_JINA_API_KEY          →  config.py (Settings)
IMAGE_SEARCH_GOOGLE_API_KEY              ↓
                              runtime._build_embedding_client(settings)
                                         ↓
                              EmbeddingClient instance
                                    ↙        ↘
                        IndexService      SearchService
                        .embedding_client  .embedding_client
```

**Key files:**
- `config.py:18-22` — `jina_api_key`, `embedding_provider`, `google_api_key` fields
- `runtime.py:84-111` — `_build_embedding_client(settings)` factory
- `services/indexing.py:30` — `self.embedding_client` (used in embed_images)
- `services/search.py:24` — `self.embedding_client` (used in embed_texts)

### system_state Table (already exists)

```sql
CREATE TABLE IF NOT EXISTS system_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

Currently stores: `last_incremental_update_at`, `last_full_rebuild_at`, `last_error_summary`.
Methods `get_system_state` / `set_system_state` already exist in `repositories/sqlite.py:755-774`.

---

## Target Architecture

### New Config Flow (DB → services)

```
Admin UI (/settings)
    ↓ PUT /api/settings/embedding
web/routes.py (settings router)
    ↓ repository.set_embedding_config()
system_state (SQLite)
    ↓ runtime_services.reload_embedding_client()
new EmbeddingClient
    ↙        ↘
IndexService  SearchService
(updated in-place)
```

### Startup Flow (DB-first with env var fallback)

```
build_runtime_services(settings)
    ↓
repository.initialize_schema()
repository.get_embedding_config()
    → if empty: fall back to settings.embedding_provider / settings.jina_api_key / etc.
    → build embedding client from resolved values
```

---

## Component Changes

### 1. `config.py` — make API key fields optional

`jina_api_key`, `google_api_key`, `embedding_provider` remain in Settings as **optional fallbacks** (backward compat). They are no longer the primary source of truth after first save via UI.

### 2. `repositories/sqlite.py` — new helper methods

```python
KEYS = {
    "provider": "config.embedding_provider",
    "jina_api_key": "config.jina_api_key",
    "google_api_key": "config.google_api_key",
}

def get_embedding_config(self) -> dict[str, str | None]:
    return {
        "provider": self.get_system_state(KEYS["provider"]),
        "jina_api_key": self.get_system_state(KEYS["jina_api_key"]),
        "google_api_key": self.get_system_state(KEYS["google_api_key"]),
    }

def set_embedding_config(
    self,
    *,
    provider: str | None = None,
    jina_api_key: str | None = None,
    google_api_key: str | None = None,
) -> None:
    if provider is not None:
        self.set_system_state(KEYS["provider"], provider)
    if jina_api_key is not None:
        self.set_system_state(KEYS["jina_api_key"], jina_api_key)
    if google_api_key is not None:
        self.set_system_state(KEYS["google_api_key"], google_api_key)
```

### 3. `runtime.py` — DB-first init + hot-reload method

**`build_runtime_services` changes:**
- After `repository.initialize_schema()`, call `repository.get_embedding_config()`
- Override settings fields with DB values if present
- Add `index_service` to `RuntimeServices` dataclass (needed for hot-reload)

**`RuntimeServices` changes:**
- Add `index_service: IndexService` field
- Add `repository: MetadataRepository` field (needed by reload to read updated config)
- Add `settings: Settings` field (needed for fallback values)
- Add `async reload_embedding_client()` method:

```python
async def reload_embedding_client(self) -> None:
    """Rebuild embedding client from DB config and swap references on all services."""
    db_config = self.repository.get_embedding_config()
    provider = db_config["provider"] or self.settings.embedding_provider
    if provider == "jina":
        api_key = db_config["jina_api_key"] or self.settings.jina_api_key
    else:
        api_key = db_config["google_api_key"] or self.settings.google_api_key

    new_client = _build_embedding_client_from(
        provider=provider,
        api_key=api_key,
        settings=self.settings,
    )
    old_client = self.embedding_client
    # Swap references atomically
    self.embedding_client = new_client
    self.search_service.embedding_client = new_client
    self.index_service.embedding_client = new_client
    # Close old client
    try:
        await old_client.aclose()
    except Exception:
        pass
```

### 4. `web/routes.py` — new settings router

```python
def create_settings_router(
    *,
    runtime_services: RuntimeServices,
    repository: MetadataRepository,
    settings: Settings,
) -> APIRouter:
    router = APIRouter(prefix="/api/settings")

    @router.get("/embedding")
    async def get_embedding_settings():
        cfg = repository.get_embedding_config()
        provider = cfg["provider"] or settings.embedding_provider
        return {
            "provider": provider,
            "jina_api_key_configured": bool(cfg["jina_api_key"] or settings.jina_api_key),
            "google_api_key_configured": bool(cfg["google_api_key"] or settings.google_api_key),
        }

    @router.put("/embedding")
    async def update_embedding_settings(payload: EmbeddingSettingsRequest):
        # Validate provider
        if payload.provider not in {"jina", "gemini"}:
            raise HTTPException(422, "provider must be 'jina' or 'gemini'")
        # Validate that the target provider has an API key (existing or new)
        cfg = repository.get_embedding_config()
        if payload.provider == "jina":
            effective_key = payload.jina_api_key or cfg["jina_api_key"] or settings.jina_api_key
        else:
            effective_key = payload.google_api_key or cfg["google_api_key"] or settings.google_api_key
        if not effective_key:
            raise HTTPException(422, f"No API key configured for provider '{payload.provider}'")
        # Save to DB (None = preserve existing)
        repository.set_embedding_config(
            provider=payload.provider,
            jina_api_key=payload.jina_api_key,
            google_api_key=payload.google_api_key,
        )
        # Hot-reload — if this fails, DB is already updated (retry is safe)
        try:
            await runtime_services.reload_embedding_client()
        except Exception as exc:
            raise HTTPException(
                500,
                f"Settings saved but embedding reload failed: {exc}",
            ) from exc
        # Return updated status
        return await get_embedding_settings()
```

### 5. `app.py` — wire settings router

Pass `runtime_services`, `repository` (from `runtime_services`), and `settings` to `create_settings_router`.

### 6. Frontend

**New files:**
- `web/src/pages/SettingsPage.tsx` — form with provider select + key inputs
- `web/src/api/settings.ts` — `useEmbeddingSettings()` + `useUpdateEmbeddingSettings()` hooks

**Modified files:**
- `web/src/App.tsx` — add `/settings` route
- `web/src/components/Layout.tsx` — add Settings nav item (Settings icon)

---

## Startup Behavior with No DB Config

On first run with no `config.*` rows in `system_state`:
- Falls back to env vars (`settings.embedding_provider`, `settings.jina_api_key`, etc.)
- If env vars also empty: RuntimeServices still builds, but `embedding_client` is `None`
- IndexService/SearchService raise `ValueError("embedding not configured")` on first use
- Admin UI shows unconfigured state prompt

## Key Invariants

- API key is **never** returned in plaintext from `GET /api/settings/embedding`
- Reload is **always** called after DB write (atomic save+reload or rollback)
- Existing env-var deployments continue working without UI interaction
