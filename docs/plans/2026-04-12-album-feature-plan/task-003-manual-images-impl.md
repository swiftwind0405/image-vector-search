# Task 003: Manual Album Image Management — Implementation

**type**: impl
**depends-on**: [003-manual-images-test, 002-album-crud-impl]

## Goal

Implement manual album image add/remove/list methods to make the image management tests pass.

## Files to Modify

- `src/image_vector_search/repositories/sqlite.py` — Add methods: `add_images_to_album`, `remove_images_from_album`, `list_album_images`
- `src/image_vector_search/services/albums.py` — Add methods: `add_images_to_album`, `remove_images_from_album`, `list_album_images`

## What to Implement

### Repository (`sqlite.py`)

- `add_images_to_album(album_id, content_hashes)` — INSERT OR IGNORE into album_images for each hash, return count of newly added rows
- `remove_images_from_album(album_id, content_hashes)` — DELETE from album_images matching album_id and content_hash IN (?), return count
- `list_album_images(album_id, limit, cursor)` — SELECT images joined with album_images, ordered by sort_order ASC then id ASC, cursor pagination on canonical_path, return `PaginatedAlbumImages`

Also update `list_albums()` to include accurate image_count for manual albums via subquery on album_images.

### Service (`albums.py`)

- `add_images_to_album` — verify album exists and is manual type, enforce MAX_BULK_SIZE, delegate to repo
- `remove_images_from_album` — verify album exists and is manual type, enforce MAX_BULK_SIZE, delegate to repo
- `list_album_images` — verify album exists, dispatch to `list_album_images` for manual or `list_smart_album_images` for smart

## Verification

```bash
pytest tests/unit/test_album_service.py -v -k "image"
# All image management tests should PASS (Green)
```
