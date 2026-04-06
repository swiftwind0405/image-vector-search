# BDD Specifications: Embedding Settings Admin UI

## Feature: Admin configures embedding provider and API keys via UI

### Background
```
Given the admin is authenticated
And the admin navigates to /settings
```

---

### Scenario 1: View current configuration (masked)
```
Given embedding provider "jina" and a Jina API key are already configured in DB
When the Settings page loads
Then the provider dropdown shows "jina"
And the Jina API key field shows a masked placeholder (e.g. "••••••")
And jina_api_key_configured indicator is true
And google_api_key_configured indicator is false
And the Save button is disabled (no unsaved changes)
```

### Scenario 2: Save new provider and API key (happy path)
```
Given provider is currently "jina"
When admin selects "gemini" from the provider dropdown
And enters a valid Gemini API key
And clicks "Save Settings"
Then PUT /api/settings/embedding is called with {provider: "gemini", google_api_key: "<key>", jina_api_key: null}
And the API returns 200 with {provider: "gemini", google_api_key_configured: true}
And a success toast "Settings saved" appears
And the embedding client hot-reloads with the new Gemini client
And the Dashboard shows "gemini" as active provider within seconds
```

### Scenario 3a: Change provider when target key already exists
```
Given provider "jina" with Jina API key configured
And Google API key is also already configured
And the admin does NOT modify either API key field
When admin changes provider to "gemini"
And clicks "Save Settings"
Then PUT /api/settings/embedding is called with {provider: "gemini", jina_api_key: null, google_api_key: null}
And backend resolves effective key as existing google_api_key (null = preserve)
And returns 200 with {provider: "gemini", google_api_key_configured: true}
And embedding client hot-reloads with Gemini
```

### Scenario 3b: Change provider when target key is missing
```
Given provider "jina" with Jina API key configured
And NO Google API key is configured (neither in DB nor env vars)
When admin changes provider to "gemini" without entering a Google API key
And clicks "Save Settings"
Then PUT /api/settings/embedding returns 422
With detail "No API key configured for provider 'gemini'"
And no changes are written to system_state
And embedding client is NOT reloaded
```

### Scenario 4: Save with invalid provider value
```
Given frontend sends {provider: "openai", api_key: "..."}  [bypassing UI validation]
When PUT /api/settings/embedding is called
Then API returns 422 Unprocessable Entity
And error detail says "provider must be 'jina' or 'gemini'"
And no changes are written to system_state
```

### Scenario 5: Reload fails after successful DB write
```
Given valid credentials are provided
When the DB write succeeds
But reload_embedding_client() raises an exception (e.g. network timeout)
Then the API returns 500 with detail "Settings saved but embedding reload failed: <reason>"
And the toast shows "Settings saved but reload failed — try again"
And a retry button appears in the UI
```

### Scenario 6: No configuration at startup (fresh install)
```
Given no config.* keys in system_state
And no embedding env vars set
When the server starts
Then RuntimeServices builds successfully (no crash)
And embedding_client is None (or raises on first use)
And GET /api/settings/embedding returns {provider: "", jina_api_key_configured: false, google_api_key_configured: false}
And the Settings page shows an "unconfigured" warning banner
```

### Scenario 7: Startup with env vars only (existing deployment)
```
Given IMAGE_SEARCH_EMBEDDING_PROVIDER=jina and IMAGE_SEARCH_JINA_API_KEY=<key> are set
And no config.* keys in system_state
When the server starts
Then embedding_client is built from env var values
And GET /api/settings/embedding returns {provider: "jina", jina_api_key_configured: true}
And the Settings page shows current env-var config read-only note
```

### Scenario 8: Frontend API key dirty-state handling
```
Given the Settings page shows masked key for provider "jina"
When admin does NOT touch the API key input
Then the PUT request sends jina_api_key: null (preserve existing)
When admin clicks into the API key input and types a new value
Then the PUT request sends jina_api_key: "<new_value>"
When admin clicks into the API key input and clears it
Then the Save button shows validation error "API key cannot be empty"
```

---

## Testing Strategy

### Backend unit tests (`tests/unit/test_settings_routes.py`)
- GET returns masked status, never plaintext
- PUT with valid provider+key → calls `set_embedding_config` + `reload_embedding_client`
- PUT with invalid provider → 422, no DB write
- PUT with null api_key → calls `set_embedding_config(jina_api_key=None)` (no-op in repo)
- Reload failure → 500 with details, DB change persisted

### Backend unit tests (`tests/unit/test_runtime_reload.py`)
- `reload_embedding_client()` updates `search_service.embedding_client`
- `reload_embedding_client()` updates `index_service.embedding_client`
- Old client's `aclose()` is called after swap
- Reload with missing API key raises `ValueError`

### Backend unit tests (`tests/unit/test_repository_embedding_config.py`)
- `get_embedding_config()` returns None for unconfigured keys
- `set_embedding_config(provider="gemini")` writes only provider key
- `set_embedding_config(jina_api_key=None)` does not overwrite existing

### Frontend tests (`web/src/test/SettingsPage.test.tsx`)
- Renders masked key indicator when `api_key_configured: true`
- Save button disabled when no fields changed (not dirty)
- PUT called with `jina_api_key: null` when key field untouched
- Shows toast on success; shows error detail on 422/500
- Retry button appears on 500 reload failure
