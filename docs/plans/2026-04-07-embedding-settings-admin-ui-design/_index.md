# Embedding Settings Admin UI — Design

**Date:** 2026-04-07  
**Status:** Design complete, ready for implementation

## Context

Currently `IMAGE_SEARCH_EMBEDDING_PROVIDER`, `IMAGE_SEARCH_JINA_API_KEY`, and `IMAGE_SEARCH_GOOGLE_API_KEY` are configured via environment variables. This change moves them to a Settings page in the admin UI, stored in SQLite `system_state`, with hot-reload (no restart required) when changed.

## Requirements

### Functional
1. New `/settings` page in admin UI with provider selector and API key inputs
2. `GET /api/settings/embedding` — returns current provider + key-configured flags (never plaintext)
3. `PUT /api/settings/embedding` — saves to DB and hot-reloads embedding client
4. Hot-reload: `RuntimeServices.reload_embedding_client()` swaps client on IndexService + SearchService without restart
5. Backward compat: if DB has no config, fall back to env vars (existing deployments unaffected)

### Non-Functional
- API key never returned in plaintext
- Reload completes within existing request lifecycle
- No DB schema changes needed (reuses `system_state` table)

### Out of Scope
- `embedding_model`, `embedding_version`, `batch_size`, rate-limit params — remain env vars
- Re-embedding existing vectors when provider changes
- API key encryption at rest (plaintext for MVP)
- Audit logging

## Rationale

**Option A (direct reference swap)** chosen over proxy pattern: RuntimeServices already owns all service references, so updating 3 fields in one method is simple and traceable. No new abstraction needed.

**DB keys used:**
- `config.embedding_provider`
- `config.jina_api_key`
- `config.google_api_key`

**Null = preserve** semantics on PUT: sending `jina_api_key: null` leaves the existing key intact, allowing provider-switch without re-entering keys.

## Detailed Design

### Backend Components

| Component | Change |
|-----------|--------|
| `config.py` | `jina_api_key`, `google_api_key`, `embedding_provider` kept as optional env fallbacks |
| `repositories/sqlite.py` | Add `get_embedding_config()` / `set_embedding_config()` helpers |
| `runtime.py` | DB-first init; add `index_service`+`repository`+`settings` to RuntimeServices; add `reload_embedding_client()` |
| `web/routes.py` | Add `create_settings_router(runtime_services, repository, settings)` |
| `app.py` | Wire settings router with RuntimeServices reference |

### Frontend Components

| Component | Change |
|-----------|--------|
| `pages/SettingsPage.tsx` | New: provider dropdown + API key inputs + save |
| `api/settings.ts` | New: `useEmbeddingSettings()` + `useUpdateEmbeddingSettings()` hooks |
| `App.tsx` | Add `/settings` route |
| `components/Layout.tsx` | Add Settings nav item |

### Edge Cases

| Case | Handling |
|------|----------|
| No config at all | Embedding client = None; settings page shows unconfigured warning |
| Reload fails after DB write | Return 500 + detail; retry button in UI; DB persists new values |
| In-flight requests during reload | Old client finishes; new client used for subsequent requests |
| User changes provider without re-entering key | `null` = preserve existing; warn if target provider has no key |

## Design Documents

- [BDD Specifications](./bdd-specs.md) — Behavior scenarios and testing strategy
- [Architecture](./architecture.md) — System architecture and component details
- [Best Practices](./best-practices.md) — Security, performance, and code quality guidelines
