# Task 004: Smart Album Rules and Query — Implementation

**type**: impl
**depends-on**: [004-smart-rules-test, 002-album-crud-impl]

## Goal

Implement smart album rule management and the real-time image matching query engine.

## Files to Modify

- `src/image_vector_search/repositories/sqlite.py` — Add methods: `set_album_rules`, `get_album_rules`, `set_album_source_paths`, `get_album_source_paths`, `list_smart_album_images`
- `src/image_vector_search/services/albums.py` — Add methods: `set_album_rules`, `get_album_rules`, `set_album_source_paths`, `get_album_source_paths`, `list_smart_album_images`

## What to Implement

### Repository (`sqlite.py`)

- `set_album_rules(album_id, rules)` — Within a transaction: DELETE all existing rules for album, INSERT new rules. Validate no duplicate tag_ids before inserting.
- `get_album_rules(album_id)` — SELECT rules joined with tags table for tag_name
- `set_album_source_paths(album_id, paths)` — Within a transaction: DELETE all existing paths, INSERT new paths
- `get_album_source_paths(album_id)` — SELECT paths for album
- `list_smart_album_images(album_id, limit, cursor)` — Build dynamic SQL query:
  1. Fetch album's rule_logic and all rules
  2. Fetch source paths
  3. If no include rules, return empty PaginatedAlbumImages
  4. Build AND or OR query (see architecture.md for SQL templates)
  5. If source paths exist, add `AND (canonical_path LIKE ? OR ...)` with path prefix matching (join images_root + source_path + '/%')
  6. If exclude tags exist, add `NOT IN` subquery
  7. Apply cursor pagination (`canonical_path > ?`) and LIMIT
  8. Return PaginatedAlbumImages

Also update `list_albums()` to include image_count for smart albums by executing a count variant of the smart album query.

### Service (`albums.py`)

- `set_album_rules` — verify album exists and is smart type, validate no duplicate tag_ids in input, delegate to repo
- `get_album_rules` — verify album exists, delegate to repo
- `set_album_source_paths` — verify album exists and is smart type, delegate to repo
- `get_album_source_paths` — verify album exists, delegate to repo

## Verification

```bash
pytest tests/unit/test_album_smart_query.py -v
# All smart album tests should PASS (Green)
```
