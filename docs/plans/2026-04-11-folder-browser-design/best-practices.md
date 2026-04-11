# Best Practices — Folder Browser

## Security

- **Path traversal**: reject any `path` query value containing `..`, backslashes, NUL bytes, or a leading `/`. Do the rejection in the route handler before touching SQL. Return `400 invalid path`.
- **Prefix safety**: build the SQL `LIKE` prefix by concatenating the normalized `images_root` with the normalized relative path and a trailing `/`. Never feed the raw client string into `LIKE`. Escape SQL `LIKE` metacharacters (`%`, `_`, `\`) in the relative-path segment so a user cannot craft a folder name that matches more than intended.
- **Auth**: this endpoint must be behind the same session middleware as the other `/api/*` admin endpoints. Add a test asserting an unauthenticated request is rejected in the same way existing admin routes reject it.
- **No filesystem I/O**: the handler reads only from SQLite. Do not `os.listdir` the `images_root` — that would leak directories that haven't been indexed and could expose arbitrary paths if `images_root` is misconfigured.

## Performance

- **Single DISTINCT scan for folders**: `list_folders()` already does one `SELECT DISTINCT canonical_path`. Don't replace it with per-request SQL; reuse it and filter in Python. At today's archive sizes (tens of thousands of images), this is sub-millisecond.
- **Index-friendly image query**: the `LIKE 'prefix%'` predicate uses the leading-wildcard-free form, so SQLite can use an index on `canonical_path` if one exists (confirm via `EXPLAIN QUERY PLAN` during implementation). If it doesn't, adding one is a one-line migration but out of scope for this task unless profiling proves it's needed.
- **Pagination**: accept `limit` (default 200, same as `/api/images` infinite loader) and a `canonical_path` cursor. Folder lists are unpaginated — the cardinality is bounded by the on-disk directory structure.
- **Caching**: React Query cache key `['folders', 'browse', path]` is enough. No need for a Cache-Control header beyond the existing defaults; the cost of a refetch is low and the data can legitimately change after an indexing job.

## Code quality / consistency

- **Match existing admin router style** (`admin_routes.py`, `admin_bulk_routes.py`): use a factory function, `APIRouter()`, `JSONResponse(jsonable_encoder(...))`, Pydantic request/response models where they add clarity.
- **Reuse `ImageRecord`**: the response's `images` field must serialize to the same JSON shape the frontend already handles on the Images page, so `GalleryCard` and `ImageModal` work without modification.
- **Frontend component scope**: `FolderCard` is a small wrapper (~20 lines) — do not extract shared "card" abstractions prematurely. `GalleryCard` is image-specific; folders are different enough to justify a separate component.
- **No new global state**. Local component state + React Query only. Path lives in the URL (the single source of truth).
- **File naming**: backend file is `admin_folder_routes.py` (singular "folder") to match the existing `admin_tag_routes.py` / `admin_bulk_routes.py` naming pattern (all singular).

## Error handling

- **Backend**: 400 for invalid paths, 401/redirect for unauthenticated (whatever the existing admin routes return today), 200 with empty arrays for valid-but-empty folders. No 404 for "folder not found" — folders are derived, not registered.
- **Frontend**: use React Query's `error` state + the existing `ErrorBoundary` component. Don't swallow errors silently.

## Testing discipline

- Follow `superpowers:test-driven-development`: write the failing test first for each BDD scenario, then implement.
- Integration tests should hit real SQLite with a temp `images_root`, not mocks. There is a reason the CLAUDE.md and existing `tests/integration/conftest.py` wire up real services — folder-path logic is exactly the kind of code that silently breaks when mocked.
- Before merging: run `pytest` (full suite), `npm --prefix src/image_vector_search/frontend run test`, and verify no existing tests regress.

## UI consistency

- Match the existing dark-curation theme: same typographic hierarchy, same card border/background treatments, same Lucide icon library.
- Folder card: use `Folder` from `lucide-react`. Keep label to a single line with CSS ellipsis for long folder names; show the full name in a `title` tooltip.
- Breadcrumbs: reuse spacing and typography from the existing page header in `Layout.tsx` rather than introducing a new component library.
- Skeleton loading state: same shape as `ImagesPage`.

## Documentation

- Update `README.md` only if it lists admin routes (it does not today — verify at implementation time; no speculative edits).
- No changes needed to `CLAUDE.md`.

## What to explicitly *not* do

- Do **not** add a "show descendants" toggle. If users need it, link to `/images?folder=<path>` (recursive semantics already exist there).
- Do **not** add folder counts or cover thumbnails to folder cards in v1 — YAGNI.
- Do **not** introduce a separate "folder tree" sidebar component. The drill-down flow is the whole point.
- Do **not** modify `/api/folders` or `/api/images`. New behavior goes in the new endpoint only.
- Do **not** expose this to the unauthenticated HTTP tool surface (`http_tool_adapter.py`) — this is an admin-only UX.
