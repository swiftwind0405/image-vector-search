# Excluded Folders: Display-Time Filtering

## Problem

Today, "Excluded Folders" only filters during scanning/indexing (`iter_image_files`). Images already present in the database — including images embedded before exclusion, or images whose folder was excluded after indexing — still appear in:

- the Images page list,
- folder browsing,
- the folder navigation tree,
- text and similarity search results,
- album image listings (manual and smart).

The user expects an excluded folder to behave as if it does not exist for **display** purposes, while leaving previously embedded vectors and metadata untouched so that re-including a folder is instantaneous.

## Goals

- Filter excluded folders out of every read path that surfaces images to a user.
- Keep all DB rows and Milvus vectors untouched. No `is_active` mutation. No purges.
- Single source of truth for the exclusion predicate (one helper, used everywhere).
- Re-including a folder requires no re-scan, no re-embed.

## Non-goals

- No new UI. The existing Settings page already manages the exclusion list.
- No changes to scan/index behavior — exclusions there already work.
- No background reconciliation jobs.

## Design

### Centralized predicate

Add a private helper on `MetadataRepository`:

```python
def _excluded_path_clause(self, images_root: str) -> tuple[str, list[str]]:
    """Return (sql_fragment, params) that excludes any canonical_path under
    a configured excluded folder. Returns ("", []) when no exclusions."""
```

The fragment looks like:

```
NOT (canonical_path LIKE ? ESCAPE '\' OR canonical_path LIKE ? ESCAPE '\' ...)
```

with one parameter per excluded folder, built as `{images_root}/{folder}/%` and properly LIKE-escaped (reuse `_escape_like_pattern`). Folders are read via `self.get_excluded_folders()`.

### Where the predicate is applied

| Location | Change |
|---|---|
| `_build_list_images_query` | Append predicate to WHERE. Used by `list_active_images*`, `list_all_images_with_labels`. Covers Images page, Tag pages, embedding-status views. |
| `list_images_in_folder` | Append predicate to WHERE. |
| `list_folders` | Filter the resulting folder set against the excluded prefixes (in Python — small list). |
| `list_album_images` | Append predicate to the JOIN/WHERE that selects images. |
| `list_smart_album_images` / `count_smart_album_images` | Same — append predicate. |
| `SearchService._resolve_results` | Compute excluded prefixes once per call; skip any result whose `canonical_path` starts with a prefix. Same place that already handles the `folder` filter. |

`StatusService.indexable_count` already excludes — no change.

### Where exclusions are intentionally NOT applied

- Index/scan paths (`indexing.py`) — already handled at scan time.
- Admin/system queries that exist purely for diagnostics (`list_inactive_images`, `read_status_aggregates`, `list_active_paths`) — these report storage-level state, not user-facing browsing. Leaving them untouched preserves the ability to inspect what is in the DB.

### Settings copy

The Settings page currently says: *"Existing images in newly excluded folders will be marked as inactive on the next scan."* This is no longer accurate. Update it to:

> *"Excluded folders are hidden from browsing, search, and albums. Existing index data is preserved, so re-including a folder is instant."*

## Tradeoffs considered

**Per-query SQL filter (chosen).** Zero data mutation, instantly reversible, one helper used everywhere. Adds 0–N `LIKE` predicates per query (N = number of excluded folders, expected small). `canonical_path` is text; `LIKE 'prefix%'` with no leading wildcard is sargable on the implicit index used for ordering. Negligible cost in practice.

**Flip `is_active=0` for affected images.** Faster reads but mutates state, and the next scan would flip rows back unless we add a second filter inside the scanner — duplicating logic. Also conflicts with "re-include is instant".

**Materialized exclusion table.** Overkill; the exclusion list is tiny and rarely changes.

## Testing

- Unit tests on `MetadataRepository`:
  - `_excluded_path_clause` returns empty when no exclusions, correct SQL/params when populated, escapes LIKE metacharacters.
  - `list_active_images_with_labels` excludes images under an excluded folder.
  - `list_images_in_folder` excludes when the queried folder is itself excluded (returns empty) and when a child folder is excluded.
  - `list_folders` omits excluded paths.
  - `list_album_images` and `list_smart_album_images` exclude.
- Unit tests on `SearchService`:
  - Text and similarity search drop results whose path falls under an excluded folder.
- Frontend: update the Settings page copy and its existing test if it asserts on the old text.

## Migration / rollout

No DB migration. No data backfill. The change is purely query-layer and takes effect the next time a user loads any list/search.
