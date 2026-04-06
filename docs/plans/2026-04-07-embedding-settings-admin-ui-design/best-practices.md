# Best Practices: Embedding Settings Admin UI

## Security

### API Key Storage
- Store API keys in plaintext in SQLite for MVP (acceptable for local/self-hosted deployment)
- **Never** return plaintext API keys in API responses — only return `api_key_configured: bool`
- Log all settings changes as audit entries but redact key values (log `api_key: [REDACTED]`)

### API Key in Transit
- HTTPS in production (existing responsibility of deployment)
- Session auth middleware already in place — settings routes inherit same protection

### Frontend
- API key inputs use `type="password"` with show/hide toggle
- Never log key values to browser console
- Clear input value after successful save (don't persist in component state)

---

## Hot-Reload Safety

### Swap Order
```python
# Correct: build new client first, then swap atomically
new_client = _build_embedding_client(...)
self.embedding_client = new_client        # 1. RuntimeServices
self.search_service.embedding_client = new_client   # 2. SearchService
self.index_service.embedding_client = new_client    # 3. IndexService
await old_client.aclose()                 # 4. Close after swap
```

### Concurrent Requests During Reload
- Python GIL + asyncio single-threaded: reference swap is effectively atomic for our use case
- Background indexing jobs use `index_service.embedding_client` — pick up new client on next invocation
- In-flight requests with old client complete normally (aclose called after swap, not during)

### Reload Failure Handling
- If `_build_embedding_client()` raises: do NOT swap — old client stays active, return 500
- If `aclose()` on old client raises: log warning, don't propagate (already swapped)

---

## API Design

### Response Shape (GET)
```json
{
  "provider": "jina",
  "jina_api_key_configured": true,
  "google_api_key_configured": false
}
```

### Request Shape (PUT)
```json
{
  "provider": "jina",
  "jina_api_key": "new-key-or-null",
  "google_api_key": "new-key-or-null"
}
```
`null` = preserve existing key (do not overwrite). This allows changing provider without re-entering the other key.

### Error Responses
- 422: Validation errors (invalid provider)
- 500: Reload failure (DB saved, client not reloaded) — include `detail` with reason

---

## Frontend UX

### Credential Input Pattern
```tsx
// Show masked placeholder when configured; clear on focus to allow re-entry
<Input
  type="password"
  placeholder={jinaKeyConfigured ? "••••••••••" : "Enter API key"}
  onChange={(e) => { setJinaKey(e.target.value); setIsDirty(true); }}
/>
```

### Dirty State
- Track whether user has modified any field
- Disable Save button when no changes made (prevents accidental re-saves)
- On provider change: mark both provider and API key fields as dirty-requiring-check

### Partial Save Feedback
- On 500 (reload failure): show persistent warning banner, not just toast
- Include retry button that calls PUT again without requiring re-entry of keys

---

## Backward Compatibility

### Migration Path
1. Existing users with env vars set → app starts normally, reads from env
2. User opens Settings page → sees current values (sourced from env)
3. User saves → DB becomes source of truth, env vars ignored on future restarts
4. To revert: delete `config.*` rows from `system_state` table

### Startup Resolution Order
```
1. Check system_state for config.embedding_provider / config.jina_api_key / config.google_api_key
2. Fall back to Settings (env vars) if DB row is absent
3. If neither source has a value → embedding_client = None, warn on startup
```

---

## Testing Conventions (match existing patterns)

- Unit tests mock repository methods using existing `unittest.mock` patterns (see `tests/unit/`)
- Integration tests use `respx` for HTTP mocking (see existing test fixtures)
- Async tests use `pytest-asyncio` with `@pytest.mark.asyncio`
- Settings/config tests: override env vars using `monkeypatch.setenv` (existing pattern in `tests/unit/test_config.py`)
