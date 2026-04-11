# Folder Browser — Admin Page

**Status**: Design approved, awaiting implementation
**Date**: 2026-04-11
**Owner**: Stanley

## Context

The admin SPA (`src/image_vector_search/frontend`) currently exposes navigation by Tag, Category, Image Library (flat), Search, Settings and Dashboard. There is no way to browse the indexed archive by its underlying filesystem hierarchy. Users organizing a large collection on disk want to walk the tree the same way Finder/Explorer does: pick a folder, see its children and its own images, drill down, come back.

The indexing pipeline already stores `canonical_path` for every image and exposes:

- `GET /api/folders` → flat, sorted list of every relative parent directory seen in the index (e.g. `["a", "a/b", "a/b/c"]`), computed by `MetadataRepository.list_folders()` (`src/image_vector_search/repositories/sqlite.py:179`).
- `GET /api/images?folder=<rel>` → images whose `canonical_path` is prefix-matched by `<images_root>/<rel>/` (recursive; used today for bulk folder tagging).

No endpoint currently returns the *immediate* children of a given folder, nor does `/api/images` support a "direct-only" (non-recursive) variant.

## Requirements

1. Add a new sidebar entry **Folders** to the admin SPA alongside Tags / Categories / Images.
2. Clicking the menu opens a page that, for any target folder (including the archive root), shows:
   - A breadcrumb trail back to the root.
   - A grid of **immediate subfolder** cards (name only).
   - Below the subfolders, a grid of the folder's **direct-child images** only (not images that live in deeper subfolders).
3. Clicking a subfolder drills down to that folder (URL updates, browser back works).
4. Clicking an image opens the same detail modal used by the Images page (tags, categories, metadata, similar-search).
5. Route shape: `/folders?path=<relative/path>`; empty / missing `path` means the archive root.
6. Behavior matches existing admin auth, styling, and React Query caching conventions.
7. Must not regress the existing `/api/folders`, `/api/images`, or bulk-folder tagging behavior.

## Rationale

**Why a new dedicated page instead of filtering on the existing Images page?**
The Images page is a flat, filter-driven library view. The user specifically asked for a Finder-like experience where "是文件夹显示文件夹, 是图片就直接显示图片" — folders and images are rendered as distinct affordances on the same page, and navigation is positional (path-based), not filter-based.

**Why a single `GET /api/folders/browse?path=` endpoint instead of two?**
One network round-trip per navigation keeps the UI snappy and avoids cross-request race conditions where the folder list arrives before the image list (or vice versa). A single endpoint also gives us one cache key per path in React Query. We rejected "extend `/api/images`" because subfolder listing is a separate concern; overloading the image endpoint would leak folder-browsing logic into code paths used by tag/category filtering.

**Why direct-children-only (non-recursive) by default?**
It matches the user's explicit answer and the mental model of a filesystem browser. Recursive view already exists implicitly: the existing Images page with the `folder` filter (prefix-matched) gives you "everything under this prefix" when needed.

**Why reuse ImageBrowser / ImageModal?**
`GalleryCard`, `ImageModal`, and `ImageInfoPanel` already implement click-to-detail, tag/category editing, and similar-image search. Reusing them means the folder view inherits future improvements for free and keeps the visual language consistent.

## Detailed Design

### Backend

**New endpoint**: `GET /api/folders/browse`

- **Query params**:
  - `path` (string, optional) — relative folder path from `images_root`. Empty / omitted / `/` means the archive root.
- **Response shape** (JSON):
  ```json
  {
    "path": "a/b",
    "parent": "a",
    "folders": ["a/b/c", "a/b/d"],
    "images": [ /* ImageRecord[] — same shape the /api/images endpoint returns */ ],
    "next_cursor": null
  }
  ```
  - `path` is the normalized canonical path of the request (empty string for root).
  - `parent` is the parent relative path, or `null` when at root.
  - `folders` contains the **full relative paths** of immediate children (not just the leaf segment), so the frontend can build the next-level URL without string concatenation.
  - `images` contains only images whose direct parent directory equals `path`.

- **Placement**: new module `src/image_vector_search/api/admin_folder_routes.py` mounted from `app.py` alongside the other admin routers. Depends on `status_service` (for image listing) and `repository` (for folder listing) — both already constructed in `RuntimeServices`.

- **Backend semantics**:
  - **Subfolder listing**: reuse `MetadataRepository.list_folders(images_root)` (already returns every seen relative parent path). In the route, filter to entries where:
    - `entry.startswith(path + "/")` (or top-level if `path == ""`)
    - `entry` has exactly one additional path segment beyond `path`.
    This keeps the single expensive `DISTINCT canonical_path` scan in one place and avoids touching SQL.
  - **Direct-only image listing**: add a new method `MetadataRepository.list_images_in_folder(path, images_root, *, limit, cursor)` that runs:
    ```sql
    SELECT * FROM images
    WHERE is_active = 1
      AND canonical_path LIKE :prefix || '%'
      AND instr(substr(canonical_path, length(:prefix) + 1), '/') = 0
    ORDER BY canonical_path ASC
    ```
    where `:prefix = images_root + '/' + path + '/'` (or `images_root + '/'` at the root). The `instr(..., '/') = 0` clause enforces "no further slashes", i.e. direct children only. Return the same `ImageRecord` shape as other listing methods so we can reuse the existing frontend card/modal components verbatim.
  - **Path safety**: reject paths containing `..`, absolute paths, or backslashes with HTTP 400. Strip leading/trailing `/`.
  - **Pagination**: for parity with `/api/images`, accept `limit` + `cursor` on the images portion. Folder subfolders are unpaginated (the typical `list_folders` set is small; if it ever isn't, pagination can be added without breaking clients).

- **Existing `/api/folders`, `/api/images`, bulk-folder endpoints are left untouched.**

### Frontend

**Routing** (`src/image_vector_search/frontend/src/App.tsx`):
- Add `<Route path="folders" element={<FoldersPage />} />`.
- `FoldersPage` reads `path` from `useSearchParams()` (not URL params), so the single route handles any depth.

**Navigation** (`src/image_vector_search/frontend/src/components/Layout.tsx`):
- Add `{ to: "/folders", icon: Folder, label: "Folders" }` to `navItems`, inserted between Categories and Images.
- Add a `pageMeta` entry for `/folders` matching the existing editorial-header style.

**API client** (`src/image_vector_search/frontend/src/api/folders.ts`, new file):
- `useFolderBrowse(path: string)` — `useQuery` against `/api/folders/browse?path=...`, key `['folders', 'browse', path]`.
- Types: `FolderBrowseResponse { path: string; parent: string | null; folders: string[]; images: ImageRecord[] }`.

**Page** (`src/image_vector_search/frontend/src/pages/FoldersPage.tsx`, new file):
- Reads `path` from `useSearchParams`.
- Calls `useFolderBrowse(path)`.
- Layout (top to bottom):
  1. **Breadcrumbs**: `Root / a / b / c`, each segment a `<Link>` to `/folders?path=<accumulated>`.
  2. **Subfolders section**: `<h3>Subfolders</h3>` + CSS grid of `FolderCard`s. Each card shows only the folder name (final segment of the relative path) and clicks to `/folders?path=<full_relative_path>`. Hidden when `folders` is empty.
  3. **Divider**.
  4. **Images section**: `<h3>Images</h3>` + reuse `GalleryGrid` / `GalleryCard` from the existing Images page, wired to open `ImageModal` on click. Hidden when `images` is empty.
  5. **Empty state**: when both `folders` and `images` are empty, show "This folder is empty.".
- Loading state matches the existing admin pages (skeleton cards).
- No folder-count / cover-thumbnail on folder cards (YAGNI, per user decision).

**Reused components**: `GalleryCard`, `GalleryGrid`, `ImageModal`, `ImageInfoPanel` — no changes required beyond whatever props they already accept.

### Data & Caching

- React Query cache key: `['folders', 'browse', path]`. Stale-while-revalidate is fine; no manual invalidation needed because folder contents only change when indexing runs, and the existing `['status']` invalidation on job completion does not need to touch this new cache (it will refetch naturally when the user re-enters a folder).

### Out of scope (YAGNI)

- Folder counts, cover thumbnails on folder cards.
- Recursive ("include descendants") toggle on this page. If needed, link out to `/images?folder=<path>`.
- Folder rename / move / delete operations.
- Filesystem-watch live updates.
- Separate tree-sidebar view.
- Bulk selection at the folder level (bulk-folder tagging is already handled by the dedicated bulk endpoints and Images page UI).

## Design Documents

- [BDD Specifications](./bdd-specs.md) — behavior scenarios and testing strategy
- [Architecture](./architecture.md) — backend module layout and request flow
- [Best Practices](./best-practices.md) — security, performance, and consistency guidelines
