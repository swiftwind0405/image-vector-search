# React Admin Frontend Design

## Summary

Migrate the admin console from Jinja2 + vanilla JS to a React SPA. The React app lives inside `src/image_vector_search/frontend/`, builds to `frontend/dist/`, and is served by FastAPI as static files. This iteration implements the existing dashboard features plus three new management pages for tags, categories, and image associations.

## Tech Stack

| Concern | Choice |
|---------|--------|
| Framework | React 18 + TypeScript (strict) |
| Build tool | Vite |
| Routing | React Router v6 |
| Server state | TanStack React Query |
| Local state | useState / useReducer |
| UI components | shadcn/ui + Tailwind CSS |
| Design style | shadcn/ui default (clean, neutral) |
| Lint / Format | ESLint + Prettier |

No global state library. No axios — plain fetch wrapper.

## Project Structure

```
src/image_vector_search/frontend/
  package.json
  tsconfig.json
  vite.config.ts
  index.html                 ← Vite entry HTML
  src/
    main.tsx                 ← React root
    App.tsx                  ← Router setup
    api/
      client.ts              ← fetch wrapper, ApiError class
      tags.ts                ← useTags, useCreateTag, useUpdateTag, useDeleteTag
      categories.ts          ← useCategories, useCreateCategory, useUpdateCategory, useDeleteCategory
      images.ts              ← useImageTags, useImageCategories, useAddTagToImage, useRemoveTagFromImage, useAddCategoryToImage, useRemoveCategoryFromImage
      jobs.ts                ← useJobs, useJob, useQueueJob
      status.ts              ← useStatus
    pages/
      DashboardPage.tsx      ← Index status, job control, job history, debug search
      TagsPage.tsx           ← Tag CRUD management
      CategoriesPage.tsx     ← Hierarchical category CRUD
      ImagesPage.tsx         ← Per-image tag/category association
    components/
      Layout.tsx             ← Sidebar nav + content area
      TagForm.tsx            ← Create/edit tag form
      CategoryTree.tsx       ← Tree view for category hierarchy
      ImageTagEditor.tsx     ← Tag/category editor for a single image
    lib/
      utils.ts               ← shadcn/ui cn() utility
  dist/                      ← Build output (gitignored)
  routes.py                  ← Existing API routes (unchanged)
  tag_routes.py              ← Existing tag API routes (unchanged)
  templates/                 ← Removed after migration
  static/                    ← Removed after migration
```

## Backend Prerequisites

The following new endpoint is required before the Images page can be built:

- **`GET /api/images`** — List all indexed images with content_hash and file path. Added to `routes.py` or `tag_routes.py`. Sources data from `MetadataRepository` (image metadata table). Supports pagination in a future iteration.

## Build Integration

### Vite Config

- `base: "/"`
- `build.outDir: "../dist"` (outputs to `frontend/dist/`)
- Dev server on port 5173, proxy `/api/*` to `http://localhost:8000`

Note: Vite's default build places JS/CSS in an `assets/` subfolder within `outDir`, so `dist/assets/` is served by the `/assets` static mount below.

### FastAPI Integration

Production mode: mount `frontend/dist/` as static files. Add SPA fallback route. **Route ordering is critical** — the catch-all must be registered last, after all API routes, the `/mcp` mount, and `/healthz`:

```python
# app.py — registration order matters
# 1. API routers (already exist): /api/*
# 2. MCP mount (already exists): /mcp
# 3. Health check (already exists): /healthz
# 4. Static assets from Vite build:
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")
# 5. SPA fallback — MUST be last:
@app.get("/{path:path}")
async def spa_fallback():
    return FileResponse("frontend/dist/index.html")
```

Remove Jinja2Templates, old `GET /` route, `/static` mount, `templates/`, and `static/` after migration.

### Package Data

`pyproject.toml` updated to include `frontend/dist/**` in package-data so the built frontend ships with the Python package.

### Docker

Multi-stage build:
1. Stage 1: `node:20-alpine` — `npm ci && npm run build` in `web/`
2. Stage 2: Python image — copy `dist/` from stage 1 into the web directory

### .gitignore

Add `src/image_vector_search/frontend/dist/` and `src/image_vector_search/frontend/node_modules/`.

## Pages

### Dashboard (`/`)

Reimplements all current admin console functionality:

- **Index status card**: progress bar + stats grid (on disk, indexed, inactive, vectors, model). Polls `GET /api/status` via React Query with `refetchInterval: 3000`.
- **Job control**: "Incremental Update" and "Full Rebuild" buttons. POST to `/api/jobs/incremental` or `/api/jobs/rebuild`.
- **Recent jobs list**: polls `GET /api/jobs` with `refetchInterval: 3000`.
- **Debug search**: text search input + submit, POST to `/api/debug/search/text`. Also a similar-image search input (content_hash), POST to `/api/debug/search/similar`. Both display JSON results in a code block.

### Tags (`/tags`)

- Tag list as a table: name, associated image count, action buttons (edit, delete).
- Create: inline input + button, or dialog. POST `/api/tags`.
- Edit: dialog with name input. PUT `/api/tags/{id}`.
- Delete: confirmation dialog. DELETE `/api/tags/{id}`.

### Categories (`/categories`)

- Tree view displaying hierarchical parent-child structure.
- Create: dialog with name input + optional parent selector. POST `/api/categories`.
- Edit: dialog to rename, move to different parent, or move to root. PUT `/api/categories/{id}` with `{name?, move_to_parent_id?, move_to_root?}`. The form offers three actions: rename, reparent (select new parent), or move to root level.
- Delete: confirmation dialog warning if children exist. DELETE `/api/categories/{id}`.
- Lazy-load children: `GET /api/categories/{id}/children` is available but the initial implementation loads the full tree via `GET /api/categories` for simplicity.

### Images (`/images`)

- Image list table showing content_hash and file path. Data from new `GET /api/images` endpoint (see Backend Prerequisites).
- Click an image row to expand/open its tag/category editor.
- Add tag: dropdown selector from existing tags. POST `/api/images/{hash}/tags` with `{"tag_id": int}`.
- Remove tag: click X on tag badge. DELETE `/api/images/{hash}/tags/{tag_id}`.
- Add category: tree selector from existing categories. POST `/api/images/{hash}/categories` with `{"category_id": int}`.
- Remove category: click X on category badge. DELETE `/api/images/{hash}/categories/{category_id}`.

## API Client Layer

### Fetch Wrapper

```typescript
// api/client.ts
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  if (res.status === 204) return undefined as T;  // DELETE endpoints return no body
  return res.json();
}
```

### React Query Conventions

- Query keys by domain: `["tags"]`, `["categories"]`, `["status"]`, `["jobs"]`, `["images", hash, "tags"]`
- Mutations invalidate related queries on success
- No optimistic updates — keep it simple for admin tooling

### Data Flow

```
User action → Component → useMutation() → apiFetch → FastAPI
                               ↓ onSuccess
                         invalidateQueries → useQuery refetch → UI update
```

## Error Handling

- `apiFetch` throws `ApiError` with HTTP status and server message.
- Mutations surface errors via shadcn/ui toast notifications.
- React Error Boundary at root level for unhandled exceptions.
- No offline support. No retry logic beyond React Query defaults.

## Navigation

Sidebar layout (`Layout.tsx`) with links:

| Icon | Label | Route |
|------|-------|-------|
| LayoutDashboard | Dashboard | `/` |
| Tag | Tags | `/tags` |
| FolderTree | Categories | `/categories` |
| Image | Images | `/images` |

Uses `lucide-react` icons (bundled with shadcn/ui).

## Migration Strategy

- One-shot replacement, not incremental migration.
- Build the full React app with all four pages.
- Once complete, remove `templates/`, `static/`, Jinja2 dependencies from `app.py`.
- Update `app.py` to serve SPA static files + fallback route.

## Out of Scope

- Image gallery / thumbnail browsing (future)
- Visual search results with image grid (future)
- Bulk operations (future)
- Settings management UI (future)
- Authentication / authorization
- OpenAPI client codegen
- SSR / SSG
- Offline support / optimistic updates
