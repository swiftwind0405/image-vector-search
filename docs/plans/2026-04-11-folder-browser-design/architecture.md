# Architecture — Folder Browser

## System view

```
┌────────────────────────────────────────────┐
│ React SPA (frontend/)                      │
│                                            │
│  Layout.tsx  ──►  FoldersPage.tsx          │
│                     │                      │
│                     ▼                      │
│           api/folders.ts (useFolderBrowse) │
└────────────────────────┬───────────────────┘
                         │ GET /api/folders/browse?path=...
                         ▼
┌────────────────────────────────────────────┐
│ FastAPI app (app.py)                       │
│                                            │
│   admin_folder_routes.py                   │
│      │                                     │
│      ├──► MetadataRepository.list_folders  │
│      │      (existing, returns flat list)  │
│      │                                     │
│      └──► MetadataRepository               │
│            .list_images_in_folder (NEW)    │
│                   │                        │
│                   ▼                        │
│            SQLite (images table)           │
└────────────────────────────────────────────┘
```

## New / modified modules

| File | Change | Notes |
|------|--------|-------|
| `src/image_vector_search/api/admin_folder_routes.py` | **New** | `create_admin_folder_router(repository, status_service, images_root)` returning a router with `GET /api/folders/browse`. |
| `src/image_vector_search/app.py` | **Modify** | Import and `app.include_router(create_admin_folder_router(...))` next to the other admin routers, gated on `runtime_services` / `repository` being available. |
| `src/image_vector_search/repositories/sqlite.py` | **Modify** | Add `list_images_in_folder(path, images_root, *, limit, cursor)` using the `instr(..., '/') = 0` direct-child SQL predicate. Reuse existing connection helper. |
| `src/image_vector_search/frontend/src/api/folders.ts` | **New** | `useFolderBrowse(path)` via React Query; types for `FolderBrowseResponse`. |
| `src/image_vector_search/frontend/src/pages/FoldersPage.tsx` | **New** | Renders breadcrumbs, subfolder grid, image grid; consumes `useFolderBrowse`; opens `ImageModal`. |
| `src/image_vector_search/frontend/src/App.tsx` | **Modify** | Add `<Route path="folders" element={<FoldersPage />} />`. |
| `src/image_vector_search/frontend/src/components/Layout.tsx` | **Modify** | Add Folders nav entry and `pageMeta` entry. |

No other files should need to change.

## Backend request flow

1. Route handler receives `path` query param (default `""`).
2. Normalize: strip leading/trailing `/`, reject if the result contains `..`, backslashes, or starts with `/`. Return 400 on rejection.
3. Fetch the full flat folder list via `repository.list_folders(images_root)` (already cached-friendly; single DISTINCT scan).
4. Compute immediate children:
   - Root (`path == ""`): entries with no `/`.
   - Non-root: entries starting with `path + "/"` whose remaining segment contains no `/`.
5. Fetch direct-child images via `repository.list_images_in_folder(path, images_root, limit=limit, cursor=cursor)`.
6. Build response `{path, parent, folders, images, next_cursor?}` and return via `JSONResponse` + `jsonable_encoder` to match the other admin routes.

## SQL — `list_images_in_folder`

```sql
SELECT *
FROM images
WHERE is_active = 1
  AND canonical_path LIKE :prefix || '%'
  AND instr(substr(canonical_path, length(:prefix) + 1), '/') = 0
  AND (:cursor IS NULL OR canonical_path > :cursor)
ORDER BY canonical_path ASC
LIMIT :limit;
```

where `:prefix` is `images_root.rstrip('/') + '/' + path.strip('/') + '/'` (or just `images_root.rstrip('/') + '/'` when `path == ""`).

**Why `instr(substr(...), '/') = 0`?** It guarantees that what remains of `canonical_path` after stripping the prefix has no further `/`, which is exactly the "direct child" condition. This is portable, index-compatible with the `LIKE 'prefix%'` prefix scan, and doesn't require regex.

## Frontend rendering contract

`FoldersPage` owns no business logic beyond:

1. Read `path` from `useSearchParams()`.
2. Call `useFolderBrowse(path)`.
3. Render:
   - `Breadcrumbs` (built from splitting `path` by `/`).
   - `<SectionHeader>Subfolders</SectionHeader>` + grid of `FolderCard` (new, but trivially small — a `<Link>` with a `Folder` icon and label).
   - `<SectionHeader>Images</SectionHeader>` + `GalleryGrid` reused from Images page, passing the `images` array directly.
   - `ImageModal` mounted at the page level, opened via the existing click handler of `GalleryCard`.
4. Hide sections that are empty; show a single "This folder is empty." message when both are.

## Auth / session

The new router is included under the same `SessionMiddleware` as the existing admin routers. No new auth plumbing is required. The frontend `apiFetch` client already sends the session cookie.

## Backwards compatibility

- `GET /api/folders` is **not** modified — bulk operations that depend on it continue working.
- `GET /api/images?folder=<rel>` retains its **recursive** (prefix-match) semantics. The direct-only behavior is only exposed via the new endpoint's `images` payload, keeping responsibilities separate.
- No database schema changes. No migrations.
