# Task 009: SettingsPage Component — Implementation

**type:** impl  
**depends-on:** ["008"]

## Goal

Create `src/image_vector_search/frontend/src/pages/SettingsPage.tsx` — the admin settings page for configuring embedding provider and API keys.

## BDD Scenarios

```gherkin
Scenario 1: View current configuration (masked)
  Given provider "jina" and Jina API key configured
  When Settings page loads
  Then provider dropdown shows "jina", key field shows masked placeholder, Save disabled

Scenario 2: Save new provider and API key
  When admin selects provider and enters key, clicks Save
  Then PUT called, success toast shown

Scenario 5: Reload failure
  When PUT returns 500
  Then "reload failed" toast + retry button

Scenario 6: No configuration
  When GET returns empty config
  Then unconfigured warning banner shown

Scenario 7: Env var config
  When GET returns config from env var fallback
  Then read-only note shown

Scenario 8: Dirty-state handling
  When fields unchanged: Save disabled
  When key field cleared: validation error shown
```

## Files to Create

- `src/image_vector_search/frontend/src/pages/SettingsPage.tsx`

## What to Implement

### Component Structure

A single page component `SettingsPage` with:

**State:**
- `provider` (controlled select, initialized from loaded settings)
- `jinaKey` and `googleKey` (string state, initialized to `""`)
- `jinaKeyDirty` and `googleKeyDirty` (boolean flags — true when user has typed in the field)
- `isSaving` (boolean — true during PUT request)
- `reloadFailed` (boolean — true when last PUT returned 500)

**Data fetching:** `useEmbeddingSettings()` from `api/settings.ts`

**Mutation:** `useUpdateEmbeddingSettings()` from `api/settings.ts`

### Layout

1. Page title "Settings"
2. Card "Embedding Configuration" containing:
   - Provider select: options "jina" and "gemini"
   - Jina API Key: `<Input type="password">` with label. Shows masked placeholder `"••••••"` when `jina_api_key_configured` and key field is untouched. Red border + error message if dirty and empty.
   - Google API Key: same pattern as Jina
   - Configured indicator badges (one per provider key)
3. "Currently using environment variable" note — show when config comes from env var (detect via `provider !== ""` and no DB config present — use a heuristic or add a flag to the API response)
4. Warning banner "Embedding not configured" when `provider === ""` and both `*_configured` are false
5. Save button (disabled when not dirty or isSaving)
6. Retry button (shown when `reloadFailed === true`)

### Save Handler

On save:
1. Validate: if any dirty key field is empty → show field error, do not submit
2. Build payload: `{provider, jina_api_key: jinaKeyDirty ? jinaKey : null, google_api_key: googleKeyDirty ? googleKey : null}`
3. Call `mutate(payload)`
4. On success: show toast "Settings saved", clear dirty state, clear key inputs
5. On 422 error: show toast with error detail
6. On 500 error: show toast "Settings saved but reload failed — try again", set `reloadFailed = true`

### Retry Handler

On retry:
1. Re-submit the last payload (or re-call mutate with current form values)
2. On success: clear `reloadFailed`, show toast "Reload succeeded"

## Verification

```bash
cd src/image_vector_search/frontend && npm test -- SettingsPage
```

All 9 tests must pass (Green).
