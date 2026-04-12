# Task 001: Database Schema and Domain Models

**type**: setup
**depends-on**: []

## Goal

Add the album database tables to `schema.sql` and create the domain models in `models.py`. This is a prerequisite for all other tasks.

## Files to Modify

- `src/image_vector_search/repositories/schema.sql` — Add 4 new tables: `albums`, `album_images`, `album_rules`, `album_source_paths`
- `src/image_vector_search/domain/models.py` — Add `Album`, `AlbumRule`, `PaginatedAlbumImages` models

## What to Implement

### Schema (`schema.sql`)

Add 4 CREATE TABLE statements with constraints as specified in the design:
- `albums` — with CHECK constraint enforcing rule_logic is NULL for manual, 'and'/'or' for smart
- `album_images` — junction table for manual albums, UNIQUE(album_id, content_hash), ON DELETE CASCADE
- `album_rules` — tag rules for smart albums, UNIQUE(album_id, tag_id), ON DELETE CASCADE on both FKs
- `album_source_paths` — source folder paths for smart albums, UNIQUE(album_id, path), ON DELETE CASCADE

Add indexes: `idx_album_images_album_id`, `idx_album_images_content_hash`, `idx_album_rules_album_id`, `idx_album_source_paths_album_id`

### Domain Models (`models.py`)

Add 3 Pydantic models following existing patterns (see `Tag`, `Category`, `PaginatedImages` for reference):
- `Album` — with `Literal['manual', 'smart']` for type, `Literal['and', 'or'] | None` for rule_logic, `source_paths: list[str]`, optional `image_count` and `cover_image`
- `AlbumRule` — with `Literal['include', 'exclude']` for match_mode, optional `tag_name` for display
- `PaginatedAlbumImages` — same pattern as existing `PaginatedImages`

## Verification

```bash
# Verify schema loads without errors
python -c "
from image_vector_search.repositories.sqlite import MetadataRepository
import tempfile, pathlib
db = MetadataRepository(pathlib.Path(tempfile.mktemp(suffix='.db')))
db.initialize_schema()
print('Schema OK')
"

# Verify models import correctly
python -c "
from image_vector_search.domain.models import Album, AlbumRule, PaginatedAlbumImages
print('Models OK')
"
```
