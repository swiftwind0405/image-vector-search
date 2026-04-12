# Task 002: Album CRUD — Implementation

**type**: impl
**depends-on**: [002-album-crud-test]

## Goal

Implement album CRUD methods in the repository and service layers to make the CRUD tests pass.

## Files to Modify

- `src/image_vector_search/repositories/sqlite.py` — Add methods: `create_album`, `list_albums`, `get_album`, `update_album`, `delete_album`
- `src/image_vector_search/services/albums.py` (NEW) — Create `AlbumService` class with CRUD methods

## What to Implement

### Repository (`sqlite.py`)

Add methods following existing patterns (see `create_tag`, `list_tags`, etc.):

- `create_album(name, type, description, rule_logic)` — INSERT into albums, return `Album` model
- `list_albums()` — SELECT all albums with image_count subquery. For manual albums count from `album_images`, for smart albums this will be added later (return 0 for now)
- `get_album(album_id)` — SELECT by id, return `Album | None`
- `update_album(album_id, name, description)` — UPDATE name and/or description, update `updated_at`
- `delete_album(album_id)` — DELETE by id (CASCADE handles cleanup)

### Service (`albums.py`)

Create `AlbumService` following `TagService` pattern:
- Constructor takes `repository: MetadataRepository`
- `create_album` — validate name (strip, non-empty), validate type ('manual'/'smart'), validate rule_logic required for smart
- `list_albums`, `get_album`, `update_album`, `delete_album` — delegate to repository with input validation

## Verification

```bash
pytest tests/unit/test_album_service.py -v
# All CRUD tests should PASS (Green)
```
