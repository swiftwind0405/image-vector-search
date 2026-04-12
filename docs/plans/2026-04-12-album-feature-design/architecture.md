# Architecture — Album Feature

## Component Overview

```
Frontend (React)
├── AlbumsPage.tsx          → GET /api/albums
├── AlbumImagesPage.tsx     → GET /api/albums/:id/images
│                           → POST/DELETE /api/albums/:id/images (manual)
│                           → GET/PUT /api/albums/:id/rules (smart)
└── api/albums.ts           → API client hooks

Backend (FastAPI)
├── api/admin_album_routes.py  → Route handlers
├── services/albums.py         → AlbumService (business logic)
├── repositories/sqlite.py     → MetadataRepository (new methods)
├── domain/models.py           → Album, AlbumRule, PaginatedAlbumImages
└── runtime.py                 → AlbumService wiring
```

## Database Layer

### New Tables

Added to `repositories/schema.sql`. All three tables use ON DELETE CASCADE for automatic cleanup.

**albums**: Core album record. `type` discriminates manual vs smart. `rule_logic` only applies to smart albums (NULL for manual).

**album_images**: Junction table for manual albums only. `sort_order` enables user-defined ordering. `UNIQUE(album_id, content_hash)` prevents duplicates.

**album_rules**: Rules for smart albums only. Each rule maps one tag with a match mode. `UNIQUE(album_id, tag_id)` prevents duplicate tag rules. ON DELETE CASCADE on `tag_id` ensures deleted tags don't leave orphan rules.

### Repository Methods

New methods on `MetadataRepository`:

```python
# Album CRUD
def create_album(self, name, type, description, rule_logic) -> Album
def list_albums(self) -> list[Album]  # with image_count subquery
def get_album(self, album_id) -> Album | None
def update_album(self, album_id, name, description) -> None
def delete_album(self, album_id) -> None

# Manual album images
def add_images_to_album(self, album_id, content_hashes) -> int
def remove_images_from_album(self, album_id, content_hashes) -> int
def list_album_images(self, album_id, limit, cursor) -> PaginatedAlbumImages

# Smart album rules
def set_album_rules(self, album_id, rules: list[dict]) -> None  # replace-all: deletes existing, inserts new within transaction. Empty list clears all rules.
def get_album_rules(self, album_id) -> list[AlbumRule]
def set_album_source_paths(self, album_id, paths: list[str]) -> None  # replace-all semantics
def get_album_source_paths(self, album_id) -> list[str]
def list_smart_album_images(self, album_id, limit, cursor) -> PaginatedAlbumImages  # uses source paths for path filtering
```

### Smart Album Query Construction

The `list_smart_album_images` method builds a dynamic SQL query based on the album's rules.

Smart album rules only match against tags, not categories. The `image_tags` rows with `category_id` are ignored.

If an album has 0 include rules (only exclude rules, or no rules at all), the query returns 0 images.

Smart albums can optionally have source paths. When source paths are set, tag rules only match images whose `canonical_path` starts with one of the specified paths (relative to `images_root`). When no source paths are set, rules apply to all images.

1. Fetch album's `rule_logic`, all rules, and source paths
2. Partition rules into include/exclude lists
3. If no include rules exist, return empty result
4. If source paths exist, add `AND (canonical_path LIKE ? OR ...)` clause using path prefix matching
5. Build query:

**AND logic** (all include tags required):
```sql
SELECT i.content_hash, i.canonical_path, i.file_size, i.mtime,
       i.mime_type, i.width, i.height, i.is_active, i.last_seen_at,
       i.embedding_provider, i.embedding_model, i.embedding_version,
       i.embedding_status, i.created_at, i.updated_at
FROM images i
JOIN image_tags it ON it.content_hash = i.content_hash AND it.tag_id IS NOT NULL
WHERE i.is_active = 1
  AND i.content_hash NOT IN (
      SELECT content_hash FROM image_tags WHERE tag_id IN (?)  -- exclude tags
  )
GROUP BY i.content_hash
HAVING COUNT(DISTINCT CASE WHEN it.tag_id IN (?) THEN it.tag_id END) = ?  -- include count
ORDER BY i.canonical_path
```

**OR logic** (any include tag matches):
```sql
SELECT DISTINCT i.content_hash, i.canonical_path, i.file_size, i.mtime,
       i.mime_type, i.width, i.height, i.is_active, i.last_seen_at,
       i.embedding_provider, i.embedding_model, i.embedding_version,
       i.embedding_status, i.created_at, i.updated_at
FROM images i
JOIN image_tags it ON it.content_hash = i.content_hash AND it.tag_id IN (?)  -- include tags
WHERE i.is_active = 1
  AND i.content_hash NOT IN (
      SELECT content_hash FROM image_tags WHERE tag_id IN (?)  -- exclude tags
  )
ORDER BY i.canonical_path
```

When exclude list is empty, the `NOT IN` subquery is omitted entirely.

Cursor pagination uses `canonical_path > ?` consistent with existing patterns.

### Cover Image Query

For `list_albums()`, the cover image is fetched via a subquery:

**Manual albums**: First image by `sort_order ASC, id ASC` (id as tiebreaker) → join to `images` table for metadata.

**Smart albums**: Execute the smart album query with `LIMIT 1` to get the first matching image.

For performance, cover images are fetched as a separate query per album (N+1 is acceptable here since album counts are typically small, < 100).

## Service Layer

`AlbumService` follows the same pattern as `TagService`:
- Constructor takes `repository: MetadataRepository`
- Input validation (empty names, type checks, album type enforcement)
- Delegates to repository methods
- No direct SQL

Key validations:
- `create_album`: name stripped and non-empty, type must be 'manual' or 'smart', rule_logic required for smart
- `add_images_to_album`: verify album exists and is manual type
- `remove_images_from_album`: verify album exists and is manual type
- `set_album_rules`: verify album exists and is smart type
- `list_album_images`: dispatches to manual or smart listing based on album type

## API Layer

New router `admin_album_routes.py` following `admin_tag_routes.py` patterns:

- Uses `get_runtime()` dependency for service access
- Auth guard via `require_auth` dependency (same as other admin routes)
- Pydantic request/response models defined inline
- HTTP error mapping: `ValueError` → 400/422, `sqlite3.IntegrityError` → 409, not found → 404

### Request/Response Models

```python
class CreateAlbumRequest(BaseModel):
    name: str
    type: Literal['manual', 'smart']
    description: str = ''
    rule_logic: Literal['and', 'or'] | None = None

class UpdateAlbumRequest(BaseModel):
    name: str | None = None
    description: str | None = None

class AddImagesRequest(BaseModel):
    content_hashes: list[str]

class RemoveImagesRequest(BaseModel):
    content_hashes: list[str]

class AlbumRuleInput(BaseModel):
    tag_id: int
    match_mode: Literal['include', 'exclude']

class SetRulesRequest(BaseModel):
    rules: list[AlbumRuleInput]
```

## Frontend

### TypeScript Types (`api/types.ts`)

```typescript
interface Album {
  id: number;
  name: string;
  type: 'manual' | 'smart';
  description: string;
  rule_logic: 'and' | 'or' | null;
  source_paths: string[];
  image_count: number;
  cover_image: ImageRecord | null;
  created_at: string;
  updated_at: string;
}

interface AlbumRule {
  id: number;
  album_id: number;
  tag_id: number;
  tag_name: string | null;
  match_mode: 'include' | 'exclude';
}
```

### API Client (`api/albums.ts`)

React Query hooks following the pattern in `api/tags.ts`:
- `useListAlbums()` — fetch all albums
- `useAlbumImages(albumId, limit)` — paginated images
- `useAlbumRules(albumId)` — smart album rules
- Mutation hooks for create, update, delete, add/remove images, set rules

### Pages

**AlbumsPage.tsx**: Grid of album cards showing cover thumbnail, name, type badge, image count. Create button opens a modal/dialog for new album.

**AlbumImagesPage.tsx**: Header with album name, type badge, and description. For manual albums: add/remove image controls. For smart albums: rule editor showing current tag rules with AND/OR toggle. Image grid reuses `GalleryGrid` component.

### Routing

```tsx
/albums → AlbumsPage
/albums/:albumId/images → AlbumImagesPage
```

### Navigation

Add "Albums" item to sidebar in `Layout.tsx`, positioned after "Tags" and "Categories".

## Files to Create

| File | Description |
|------|-------------|
| `src/image_vector_search/services/albums.py` | AlbumService |
| `src/image_vector_search/api/admin_album_routes.py` | API routes |
| `src/image_vector_search/frontend/src/api/albums.ts` | API client hooks |
| `src/image_vector_search/frontend/src/pages/AlbumsPage.tsx` | Album listing page |
| `src/image_vector_search/frontend/src/pages/AlbumImagesPage.tsx` | Album detail page |
| `tests/unit/test_album_service.py` | Unit tests |
| `tests/integration/test_album_api.py` | Integration tests |

## Files to Modify

| File | Changes |
|------|---------|
| `src/image_vector_search/repositories/schema.sql` | Add 3 tables + indexes |
| `src/image_vector_search/repositories/sqlite.py` | Add album repository methods |
| `src/image_vector_search/domain/models.py` | Add Album, AlbumRule, PaginatedAlbumImages |
| `src/image_vector_search/runtime.py` | Wire AlbumService into RuntimeServices |
| `src/image_vector_search/app.py` | Include album router |
| `src/image_vector_search/frontend/src/api/types.ts` | Add Album, AlbumRule interfaces |
| `src/image_vector_search/frontend/src/App.tsx` | Add album routes |
| `src/image_vector_search/frontend/src/components/Layout.tsx` | Add sidebar nav item |
