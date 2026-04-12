# Best Practices — Album Feature

## Database

### SQL Injection Prevention
- All queries use parameterized statements (`?` placeholders), never string interpolation
- Follow existing MetadataRepository patterns for parameter binding
- Smart album query construction uses `?` placeholders even for dynamically-built IN clauses

### Transaction Safety
- `set_album_rules` should delete existing rules and insert new ones within a single transaction
- `add_images_to_album` with multiple hashes uses `INSERT OR IGNORE` for idempotency
- `delete_album` relies on CASCADE for cleanup — no manual multi-table deletes needed

### Migration Strategy
- Add new `CREATE TABLE IF NOT EXISTS` statements to `schema.sql`
- `MetadataRepository.initialize_schema()` already runs all DDL on startup
- No migration tool needed — `IF NOT EXISTS` makes it safe to add to existing databases

### Index Strategy
- `idx_album_images_album_id` — fast lookup of images in an album
- `idx_album_images_content_hash` — fast lookup of albums containing an image
- `idx_album_rules_album_id` — fast rule fetch for smart album queries
- Smart album queries leverage existing `idx_image_tags_tag_id` index

## API Design

### Consistency with Existing Endpoints
- Use same pagination pattern: `?limit=N&cursor=S`, return `{items, next_cursor}`
- Use same auth guard: `require_auth` dependency
- Use same error response format
- Same `get_runtime()` dependency injection

### Idempotency
- `POST /api/albums/{id}/images` with duplicate hashes: use `INSERT OR IGNORE`, return count of newly added
- `PUT /api/albums/{id}/rules`: replace-all semantics (delete + insert) — always idempotent

### Type Safety
- Album type enforcement at service level: reject image add/remove for smart albums, reject rule set for manual albums
- Return 400 with descriptive error message, not 500

## Frontend

### Component Reuse
- Reuse `GalleryGrid`, `ImageModal`, `ImageInfoPanel` — don't create album-specific variants
- Follow the same React Query pattern as `tags.ts` for cache invalidation
- Use same pagination loading pattern as `ImagesPage`

### Optimistic Updates
- Album CRUD mutations should invalidate the albums list query on success
- Image add/remove should invalidate both the album images query and the albums list (for count update)

### State Management
- Smart album rule editor: local state for draft rules, submit sends full rule set via PUT
- No global state needed — React Query handles server state

## Performance

### Smart Album Query Efficiency
- For typical usage (< 100K images, < 50 rules): SQLite handles this in milliseconds
- The query uses existing indexes on `image_tags(tag_id)` and `images(content_hash)`
- No pre-computation or caching needed at this scale

### Cover Image Loading
- Cover images are part of the album list response — one query per album for cover
- For album counts up to ~100, N+1 is acceptable
- If album count grows significantly, batch cover fetching can be added later

### Pagination
- Smart album queries use cursor-based pagination (`canonical_path > ?` with `LIMIT`)
- Manual album queries use cursor on `sort_order` or `canonical_path`
- Consistent with existing `list_images` pagination

## Security

### Auth
- All album endpoints require authentication (same as tag/category endpoints)
- No per-album access control needed — all albums are visible to authenticated users

### Input Validation
- Album name: strip whitespace, reject empty
- Album type: Literal['manual', 'smart'] enforced by Pydantic
- Rule match_mode: Literal['include', 'exclude'] enforced by Pydantic
- content_hashes: validate format (hex string of correct length) if needed
- Bulk operations: enforce MAX_BULK_SIZE limit consistent with TagService

### Path Traversal
- Not applicable — albums don't involve filesystem paths
- Image references use content_hash, not file paths
