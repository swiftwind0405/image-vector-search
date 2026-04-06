# Task 008: SettingsPage Component — Tests

**type:** test  
**depends-on:** ["007"]

## Goal

Write frontend component tests for `SettingsPage.tsx` covering all 8 BDD scenarios that involve the settings UI.

## BDD Scenarios

```gherkin
Scenario 1: View current configuration (masked)
  Given GET /api/settings/embedding returns {provider: "jina", jina_api_key_configured: true, google_api_key_configured: false}
  When the Settings page renders
  Then provider dropdown shows "jina"
  And Jina key field shows masked placeholder "••••••"
  And jina_api_key_configured badge is visible
  And Save button is disabled

Scenario 2: Save new provider and API key (happy path)
  Given the page is loaded
  When admin changes provider to "gemini" and enters a Google API key
  And clicks "Save Settings"
  Then PUT /api/settings/embedding is called with {provider: "gemini", google_api_key: "<key>", jina_api_key: null}
  And success toast "Settings saved" appears

Scenario 3b: Change provider when target key is missing
  Given no Google API key is configured
  And PUT returns 422 "No API key configured for provider 'gemini'"
  When admin changes to gemini and saves
  Then error toast shows the 422 detail message

Scenario 5: Reload fails after successful DB write
  Given PUT returns 500 "Settings saved but embedding reload failed: timeout"
  When admin submits valid settings
  Then toast shows "Settings saved but reload failed — try again"
  And a "Retry" button appears

Scenario 6: No configuration at startup
  Given GET returns {provider: "", jina_api_key_configured: false, google_api_key_configured: false}
  When the Settings page renders
  Then an "unconfigured" warning banner is visible
  And Save button is disabled

Scenario 7: Startup with env vars only
  Given GET returns {provider: "jina", jina_api_key_configured: true} (from env var fallback)
  When the Settings page renders
  Then provider shows "jina" and key is shown as configured
  And a read-only note "Currently using environment variable" is shown

Scenario 8: Frontend dirty-state handling
  Given the Settings page is loaded with existing config
  When admin does NOT modify any fields
  Then Save button is disabled
  When admin modifies the provider dropdown
  Then Save button becomes enabled
  When admin clicks into a key field and clears it
  Then a validation error "API key cannot be empty" appears on that field
  And Save button is disabled
```

## Files to Create

- `src/image_search_mcp/web/src/test/SettingsPage.test.tsx`

## Test Cases

1. `test_renders_masked_key_when_configured` — Scenario 1
2. `test_save_button_disabled_when_no_changes` — Scenario 1 (dirty state)
3. `test_put_called_with_null_for_untouched_key` — Scenario 8 (null semantics)
4. `test_success_toast_on_save` — Scenario 2
5. `test_422_error_shown_as_toast` — Scenario 3b
6. `test_500_shows_retry_button` — Scenario 5
7. `test_unconfigured_warning_banner` — Scenario 6
8. `test_env_var_note_shown` — Scenario 7
9. `test_clear_key_field_disables_save` — Scenario 8

## Test Setup Pattern

Follow the existing patterns in `src/image_search_mcp/web/src/test/auth-flow.test.tsx`:
- Use `@testing-library/react` for rendering
- Mock API hooks using `vi.mock("@/api/settings")`
- Wrap in required providers (QueryClient, BrowserRouter)

## Verification

```bash
cd src/image_search_mcp/web && npm test -- SettingsPage
```

All 9 tests must fail (Red) before implementation.
