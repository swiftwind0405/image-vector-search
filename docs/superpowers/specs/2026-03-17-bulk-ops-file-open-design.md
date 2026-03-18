# Bulk Operations & File Open Design

## Summary

Add bulk tag/category operations (by selection and by folder), folder-based filtering, and file open/reveal to the admin console Images page. Backend provides batch API endpoints; frontend adds checkbox selection, a floating bulk action bar, folder filter, and file action buttons.

## Path Handling

`canonical_path` in the `images` table stores **absolute paths** (e.g., `/data/images/nature/flowers/rose.jpg`). All folder-related APIs work with **relative paths** (relative to `settings.images_root`):

- `list_folders()` strips the `images_root` prefix from `canonical_path` before extracting parent directories. Returns relative paths like `nature/flowers`.
- Folder filtering converts the relative `folder` param back to an absolute prefix (`images_root / folder`) before querying with `LIKE`.
- The frontend only sees and sends relative paths.

## New Backend Endpoints

### Folder Listing & Filtering

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `GET /api/folders` | GET | `string[]` | Distinct parent directories from active images' canonical_path, relative to images_root, sorted |
| `GET /api/images?folder=X` | GET | `ImageRecord[]` | Existing endpoint extended with optional `folder` query param (relative path) for path prefix filtering |

### Bulk Operations by Selection

| Endpoint | Request Body | Response | Description |
|----------|-------------|----------|-------------|
| `POST /api/bulk/tags/add` | `{ content_hashes: string[], tag_id: int }` | `{ ok: true, affected: int }` | Add tag to multiple images |
| `POST /api/bulk/tags/remove` | `{ content_hashes: string[], tag_id: int }` | `{ ok: true, affected: int }` | Remove tag from multiple images |
| `POST /api/bulk/categories/add` | `{ content_hashes: string[], category_id: int }` | `{ ok: true, affected: int }` | Add category to multiple images |
| `POST /api/bulk/categories/remove` | `{ content_hashes: string[], category_id: int }` | `{ ok: true, affected: int }` | Remove category from multiple images |

### Bulk Operations by Folder

| Endpoint | Request Body | Response | Description |
|----------|-------------|----------|-------------|
| `POST /api/bulk/folder/tags/add` | `{ folder: string, tag_id: int }` | `{ ok: true, affected: int }` | Add tag to all images in folder |
| `POST /api/bulk/folder/tags/remove` | `{ folder: string, tag_id: int }` | `{ ok: true, affected: int }` | Remove tag from all images in folder |
| `POST /api/bulk/folder/categories/add` | `{ folder: string, category_id: int }` | `{ ok: true, affected: int }` | Add category to all images in folder |
| `POST /api/bulk/folder/categories/remove` | `{ folder: string, category_id: int }` | `{ ok: true, affected: int }` | Remove category from all images in folder |

### File Operations

| Endpoint | Request Body | Response | Description |
|----------|-------------|----------|-------------|
| `POST /api/files/open` | `{ path: string }` | `{ ok: true }` | Open file with system default app |
| `POST /api/files/reveal` | `{ path: string }` | `{ ok: true }` | Reveal file in system file manager |

## Database Layer

### New Repository Methods

- `list_active_images(folder: str | None = None)` — Extend existing method. When `folder` is provided, convert relative folder to absolute prefix (`images_root / folder`) and filter with `WHERE canonical_path LIKE '{absolute_prefix}%'`. The `images_root` parameter is passed from the service layer.
- `list_folders(images_root: str)` — Extract distinct parent directories from `canonical_path` of active images, strip `images_root` prefix, return relative paths as `list[str]`.
- `bulk_add_tag(content_hashes: list[str], tag_id: int) -> int` — Single `INSERT OR IGNORE INTO image_tags` for all hashes in one transaction. Returns affected row count. FK constraints on `tag_id` validate the tag exists; FK violation raises `sqlite3.IntegrityError` which the service translates to `ValueError`.
- `bulk_remove_tag(content_hashes: list[str], tag_id: int) -> int` — Single `DELETE FROM image_tags WHERE content_hash IN (...) AND tag_id = ?`. Returns affected count.
- `bulk_add_category(content_hashes: list[str], category_id: int) -> int` — Same pattern as tags. FK constraints validate category_id.
- `bulk_remove_category(content_hashes: list[str], category_id: int) -> int` — Same pattern as tags.

**Note on idempotency:** The existing single-image `add_tag_to_image` uses plain `INSERT` which raises on duplicates. Bulk operations intentionally use `INSERT OR IGNORE` for batch safety — silently skipping already-existing associations is the correct behavior when operating on hundreds of images at once. The single-image endpoints are not changed.

### Service Layer

`TagService` new methods (TagService already has `self._repo: MetadataRepository`, so no new dependencies are needed):

- `bulk_add_tag(content_hashes, tag_id) -> int` — Validates list size (≤ 500), delegates to repository. Catches `sqlite3.IntegrityError` and raises `ValueError` for invalid tag_id.
- `bulk_remove_tag(content_hashes, tag_id) -> int`
- `bulk_add_category(content_hashes, category_id) -> int` — Same validation pattern.
- `bulk_remove_category(content_hashes, category_id) -> int`
- `bulk_folder_add_tag(folder, tag_id, images_root) -> int` — Queries `self._repo.list_active_images(folder, images_root)` to get content_hashes, then calls `self.bulk_add_tag`. Both query and write happen in a single repository method call for atomicity (see Transaction Scope below).
- `bulk_folder_remove_tag(folder, tag_id, images_root) -> int` — Same pattern
- `bulk_folder_add_category(folder, category_id, images_root) -> int`
- `bulk_folder_remove_category(folder, category_id, images_root) -> int`

`StatusService` changes:

- `list_active_images(folder: str | None = None)` — Pass folder param to repository

New functions at routes level:

- `open_file(path: str, images_root: Path)` — Validate path, use `asyncio.to_thread(subprocess.run, ["open", path])` (macOS) or `xdg-open` (Linux) to avoid blocking the event loop.
- `reveal_file(path: str, images_root: Path)` — Validate path, use `asyncio.to_thread(subprocess.run, ["open", "-R", path])` (macOS) or `xdg-open` on parent dir (Linux).

### Transaction Scope

- **Bulk by selection:** Single connection, single transaction wrapping the INSERT/DELETE for all hashes.
- **Bulk by folder:** Single connection, single transaction wrapping both the SELECT (to resolve folder → hashes) and the INSERT/DELETE. This ensures atomicity — no images are added/removed between the query and the write. Implemented as dedicated repository methods (e.g., `bulk_folder_add_tag(folder, tag_id, images_root)`) rather than composing separate query + write calls.

## File Operation Security

- Path must resolve to a location inside `settings.images_root` using `Path.resolve()` + `is_relative_to(images_root)`
- Path outside images_root → HTTP 400 `{ "detail": "Path is outside images root" }`
- File must exist (`Path.exists()`) → HTTP 404 `{ "detail": "File not found" }`
- Platform detection: `sys.platform == "darwin"` for macOS commands, fallback to `xdg-open` for Linux
- Subprocess execution uses `asyncio.to_thread(subprocess.run, ...)` to avoid blocking the async event loop
- If subprocess fails (e.g., Docker container, non-zero exit code) → HTTP 500 `{ "detail": "File operation not available in this environment" }`
- Frontend detects failure and shows a "copy path" fallback

## Bulk Operation Constraints

- `content_hashes` array maximum size: 500. Return 400 if exceeded.
- All bulk database operations use a single transaction for atomicity.
- Idempotent: duplicate add/remove operations are silently ignored (INSERT OR IGNORE / DELETE with no error on zero rows).
- Return `{ ok: true, affected: N }` where N is the actual number of rows changed.

## Frontend Changes

### Images Page Modifications

**Folder filter (top of page):**
- Select dropdown populated by `GET /api/folders`
- Options: "All folders" (default) + folder paths (relative to images_root)
- Selecting a folder passes `?folder=` param to `useImages(folder)`
- Next to the dropdown: "Folder Actions" button (enabled only when a specific folder is selected)

**Table modifications:**
- New first column: checkbox (header has select-all checkbox)
- Each row: two new icon buttons (Folder icon for reveal, FileOpen icon for open file)
- Footer text: "N images selected" when selection is active

**Bulk action bar (floating bottom):**
- Appears when >= 1 image is selected, fixed position at bottom of viewport
- Content: "N selected" label + tag dropdown + "Add Tag" / "Remove Tag" buttons + category dropdown + "Add Category" / "Remove Category" buttons
- On success: toast notification, clear selection, invalidate image queries

**Folder quick actions dialog:**
- Triggered by "Folder Actions" button next to folder filter
- Dialog shows current folder path
- Tag dropdown + "Add Tag" / "Remove Tag" buttons
- Category dropdown + "Add Category" / "Remove Category" buttons
- Calls `/api/bulk/folder/*` endpoints directly (no image selection needed)

### New API Hooks

```typescript
// Folder listing
useFolders()

// Bulk by selection
useBulkAddTag()
useBulkRemoveTag()
useBulkAddCategory()
useBulkRemoveCategory()

// Bulk by folder
useBulkFolderAddTag()
useBulkFolderRemoveTag()
useBulkFolderAddCategory()
useBulkFolderRemoveCategory()

// File operations
useOpenFile()
useRevealFile()
```

### Folder Display

Folder paths displayed relative to `images_root` for readability. E.g., if `images_root` is `/data/images`, then `/data/images/nature/flowers/` displays as `nature/flowers`.

## Out of Scope

- Folder tree navigation (flat list is sufficient)
- Image thumbnails / preview
- Pagination
- Drag-and-drop operations
- Keyboard shortcuts for selection
