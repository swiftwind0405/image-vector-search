# Album Feature Design

## Context

The image vector search application needs an album feature to organize images into collections. Two album types are required:

- **Manual albums** (普通相册): Users manually add/remove images. An image can belong to multiple albums.
- **Smart albums** (智能相册): Define rules based on tags with AND/OR logic. Images matching rules are automatically included via real-time query.

### Current State

- Images are identified by `content_hash` (SHA-256 of file contents)
- A tagging system exists: flat `tags` table and hierarchical `categories` table, linked via `image_tags` junction table
- The codebase follows a layered architecture: domain models → repository (SQLite) → service → API routes → React frontend
- Services are wired via `RuntimeServices` dataclass in `runtime.py`

## Requirements

### Functional

1. **Album CRUD**: Create, list, update (name/description), delete albums of both types
2. **Manual album - image management**: Add/remove images, support bulk operations, an image can belong to multiple albums
3. **Smart album - rule management**: Define rules using tags with include/exclude mode and AND/OR combination logic
4. **Smart album - source paths**: Smart albums can optionally specify multiple source folder paths; tag rules only match images within those paths
5. **Smart album - real-time query**: When viewing a smart album, matching images are queried in real-time (no pre-computation)
5. **Cover image**: Automatically use the first image in the album as cover (by sort_order for manual, by query result for smart)
6. **Pagination**: Album image listing supports cursor-based pagination consistent with existing patterns

### Non-Functional

1. Follow existing codebase patterns (service layer delegates to repository, Pydantic domain models, FastAPI routes)
2. Independent tables - no modification to existing tags/categories schema
3. Smart album queries must be efficient for typical tag counts (< 50 rules per album)

## Rationale

### Why independent tables (not reusing image_tags)?

The existing `image_tags` table has a strict XOR constraint (`tag_id IS NOT NULL != category_id IS NOT NULL`). Albums are a distinct organizational concept from tags/categories. Adding an `album_id` column would require breaking the XOR constraint and adding complexity to an already-loaded junction table. Independent tables keep albums decoupled and allow independent evolution.

### Why real-time query for smart albums?

Pre-computing and caching smart album membership adds complexity (cache invalidation on tag changes, storage overhead). For typical workloads (< 100K images, < 50 rules per smart album), SQLite can execute the matching query in milliseconds. Real-time query is simpler and always consistent.

### Why AND/OR at album level (not per-rule)?

A single `rule_logic` field on the album ('and' or 'or') determines how all included tags combine. This is simpler than per-rule grouping and covers the most common use cases. Users who need complex boolean logic can create multiple smart albums.

## Detailed Design

### Database Schema

Four new tables added to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS albums (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    type        TEXT NOT NULL CHECK(type IN ('manual', 'smart')),
    description TEXT NOT NULL DEFAULT '',
    rule_logic  TEXT CHECK(
        (type = 'manual' AND rule_logic IS NULL) OR
        (type = 'smart' AND rule_logic IN ('and', 'or'))
    ),
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS album_images (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id      INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    content_hash  TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    added_at      TEXT NOT NULL,
    UNIQUE(album_id, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_album_images_album_id ON album_images(album_id);
CREATE INDEX IF NOT EXISTS idx_album_images_content_hash ON album_images(content_hash);

CREATE TABLE IF NOT EXISTS album_rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id    INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    match_mode  TEXT NOT NULL CHECK(match_mode IN ('include', 'exclude')),
    UNIQUE(album_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_album_rules_album_id ON album_rules(album_id);

CREATE TABLE IF NOT EXISTS album_source_paths (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    album_id    INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    UNIQUE(album_id, path)
);

CREATE INDEX IF NOT EXISTS idx_album_source_paths_album_id ON album_source_paths(album_id);
```

Key constraints:
- `albums.name` is unique
- `albums.rule_logic` is nullable (only used for smart albums, NULL for manual)
- `album_images` only used for manual albums; ON DELETE CASCADE cleans up when album or image is deleted
- `album_rules` only used for smart albums; ON DELETE CASCADE on both album and tag ensures cleanup
- `album_source_paths` only used for smart albums; stores folder paths to limit the scope of tag matching. When empty, rules apply to all images. Paths are relative to `images_root`.

### Smart Album Query Logic

For a smart album with `rule_logic = 'and'`, include tags [A, B], exclude tag [C], and source paths ["/photos/2025", "/photos/travel"]:

```sql
SELECT DISTINCT i.* FROM images i
JOIN image_tags it ON it.content_hash = i.content_hash AND it.tag_id IS NOT NULL
WHERE i.is_active = 1
  AND (i.canonical_path LIKE '/root/photos/2025/%' OR i.canonical_path LIKE '/root/photos/travel/%')  -- source path filter (omitted when no source paths)
  AND i.content_hash NOT IN (
      SELECT content_hash FROM image_tags WHERE tag_id IN (<exclude_tag_ids>)
  )
GROUP BY i.content_hash
HAVING COUNT(DISTINCT CASE WHEN it.tag_id IN (<include_tag_ids>) THEN it.tag_id END)
       = <number_of_include_tags>
ORDER BY i.canonical_path
```

For `rule_logic = 'or'`: remove the HAVING clause, just require at least one include tag match.

### Domain Models

New models in `domain/models.py`:

```python
class Album(BaseModel):
    id: int
    name: str
    type: Literal['manual', 'smart']
    description: str
    rule_logic: Literal['and', 'or'] | None
    source_paths: list[str] = []  # smart albums only: folder paths to limit scope
    created_at: datetime
    updated_at: datetime
    image_count: int | None = None
    cover_image: ImageRecord | None = None

class AlbumRule(BaseModel):
    id: int
    album_id: int
    tag_id: int
    tag_name: str | None = None
    match_mode: Literal['include', 'exclude']

class PaginatedAlbumImages(BaseModel):
    items: list[ImageRecordWithLabels] = []
    next_cursor: str | None = None
```

### Service Layer

New `services/albums.py` with `AlbumService`:

```python
class AlbumService:
    MAX_BULK_SIZE = 500

    def __init__(self, *, repository: MetadataRepository) -> None:
        self._repo = repository

    # Album CRUD
    def create_album(self, name, type, description, rule_logic) -> Album
    def list_albums(self) -> list[Album]  # includes image_count and cover
    def get_album(self, album_id) -> Album
    def update_album(self, album_id, name, description) -> None
    def delete_album(self, album_id) -> None

    # Manual album image management
    def add_images_to_album(self, album_id, content_hashes) -> int
    def remove_images_from_album(self, album_id, content_hashes) -> int
    def list_album_images(self, album_id, limit, cursor) -> PaginatedAlbumImages

    # Smart album rule management
    def set_album_rules(self, album_id, rules: list[dict]) -> None
    def get_album_rules(self, album_id) -> list[AlbumRule]
    def set_album_source_paths(self, album_id, paths: list[str]) -> None
    def get_album_source_paths(self, album_id) -> list[str]
    def list_smart_album_images(self, album_id, limit, cursor) -> PaginatedAlbumImages
```

### API Routes

New `api/admin_album_routes.py`:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/albums` | Create album |
| GET | `/api/albums` | List all albums (with counts + covers) |
| GET | `/api/albums/{album_id}` | Get album detail |
| PUT | `/api/albums/{album_id}` | Update album name/description |
| DELETE | `/api/albums/{album_id}` | Delete album |
| GET | `/api/albums/{album_id}/images` | List images (paginated) |
| POST | `/api/albums/{album_id}/images` | Add images (manual only) |
| DELETE | `/api/albums/{album_id}/images` | Remove images (manual only) |
| GET | `/api/albums/{album_id}/rules` | Get smart album rules |
| PUT | `/api/albums/{album_id}/rules` | Set smart album rules (replace all) |
| GET | `/api/albums/{album_id}/source-paths` | Get smart album source paths |
| PUT | `/api/albums/{album_id}/source-paths` | Set smart album source paths (replace all) |

### Frontend

**New files:**
- `api/albums.ts` — API client hooks (useListAlbums, useAlbumImages, etc.)
- `pages/AlbumsPage.tsx` — Album listing with cover thumbnails and image counts
- `pages/AlbumImagesPage.tsx` — Album detail showing images (reuses GalleryGrid)

**Modified files:**
- `api/types.ts` — Add Album, AlbumRule TypeScript interfaces
- `App.tsx` — Add `/albums` and `/albums/:albumId/images` routes
- `components/Layout.tsx` — Add Albums nav item in sidebar

**Component reuse:**
- `GalleryGrid` for image display
- `ImageModal` for full-screen viewing
- `ImageInfoPanel` for metadata

### Runtime Wiring

Add `album_service: AlbumService` to `RuntimeServices` dataclass. Initialize in `build_runtime_services()`:

```python
album_service = AlbumService(repository=repository)
```

## Design Documents

- [BDD Specifications](./bdd-specs.md) - Behavior scenarios and testing strategy
- [Architecture](./architecture.md) - System architecture and component details
- [Best Practices](./best-practices.md) - Security, performance, and code quality guidelines
