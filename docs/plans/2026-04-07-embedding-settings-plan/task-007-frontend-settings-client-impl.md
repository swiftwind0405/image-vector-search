# Task 007: Frontend Settings API Client — Implementation

**type:** impl  
**depends-on:** ["006"]

## Goal

Create `src/image_search_mcp/web/src/api/settings.ts` with React Query hooks for the embedding settings endpoints. Add the corresponding TypeScript types to `api/types.ts`.

## BDD Scenario

```gherkin
Scenario: Frontend API client fetches and updates settings
  Given the backend exposes GET and PUT /api/settings/embedding
  When useEmbeddingSettings() is called
  Then it returns {provider, jina_api_key_configured, google_api_key_configured}
  When useUpdateEmbeddingSettings().mutate(payload) is called
  Then PUT /api/settings/embedding is called with the payload
  And the query cache for ["settings", "embedding"] is invalidated on success
```

## Files to Create / Modify

- **Create**: `src/image_search_mcp/web/src/api/settings.ts`
- **Modify**: `src/image_search_mcp/web/src/api/types.ts`

## What to Implement

### Types in `api/types.ts`

Add:
```typescript
export interface EmbeddingSettings {
  provider: string;
  jina_api_key_configured: boolean;
  google_api_key_configured: boolean;
}

export interface UpdateEmbeddingSettingsRequest {
  provider: string;
  jina_api_key: string | null;
  google_api_key: string | null;
}
```

### Hooks in `api/settings.ts`

**`useEmbeddingSettings()`**: `useQuery` on `["settings", "embedding"]` → `GET /api/settings/embedding`

**`useUpdateEmbeddingSettings()`**: `useMutation` → `PUT /api/settings/embedding` (JSON body), on success invalidate `["settings", "embedding"]`

Follow the existing pattern in `api/status.ts` and `api/jobs.ts` (use `apiFetch` from `api/client.ts`).

## Verification

Verified by `SettingsPage` component tests in task-008. No separate test file for this task.

Manually verify TypeScript types compile without errors:
```bash
cd src/image_search_mcp/web && npx tsc --noEmit
```
