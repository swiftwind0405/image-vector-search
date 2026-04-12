# Task 005: Cover Image and Album Listing — Implementation

**type**: impl
**depends-on**: [005-cover-image-test, 003-manual-images-impl, 004-smart-rules-impl]

## Goal

Implement cover image fetching in `list_albums()` for both manual and smart albums.

## Files to Modify

- `src/image_vector_search/repositories/sqlite.py` — Update `list_albums()` to fetch cover images

## What to Implement

### Repository (`sqlite.py`)

Update `list_albums()` to:
1. Fetch all albums with image_count (already partially done in task 002/003/004)
2. For each album, fetch the cover image:
   - **Manual albums**: Query `album_images` joined with `images` table, ORDER BY `sort_order ASC, album_images.id ASC`, LIMIT 1
   - **Smart albums**: Execute `list_smart_album_images(album_id, limit=1, cursor=None)` and take the first result
3. Set `cover_image` on the Album model (as `ImageRecord` or None)

N+1 queries for cover images are acceptable per the design decision (album counts typically < 100).

## Verification

```bash
pytest tests/unit/test_album_service.py -v -k "cover or listing"
# All cover/listing tests should PASS (Green)
```
