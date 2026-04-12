# Task 008: Frontend API Client and Types

**type**: impl
**depends-on**: [007-api-impl]

## Goal

Add TypeScript types and API client hooks for the album feature.

## Files to Modify

- `src/image_vector_search/frontend/src/api/types.ts` — Add `Album`, `AlbumRule` interfaces

## Files to Create

- `src/image_vector_search/frontend/src/api/albums.ts` — API client hooks

## What to Implement

### Types (`types.ts`)

Add interfaces following existing patterns (see `Tag`, `Category`):
- `Album` — id, name, type, description, rule_logic, source_paths, image_count, cover_image, created_at, updated_at
- `AlbumRule` — id, album_id, tag_id, tag_name, match_mode

### API Client (`albums.ts`)

Create React Query hooks following the pattern in `api/tags.ts`:
- `useListAlbums()` — GET /api/albums
- `useAlbum(albumId)` — GET /api/albums/:id
- `useAlbumImages(albumId, limit)` — GET /api/albums/:id/images with pagination
- `useAlbumRules(albumId)` — GET /api/albums/:id/rules
- `useAlbumSourcePaths(albumId)` — GET /api/albums/:id/source-paths
- `useCreateAlbum()` — POST mutation
- `useUpdateAlbum()` — PUT mutation
- `useDeleteAlbum()` — DELETE mutation
- `useAddImagesToAlbum()` — POST /api/albums/:id/images mutation
- `useRemoveImagesFromAlbum()` — DELETE /api/albums/:id/images mutation
- `useSetAlbumRules()` — PUT mutation
- `useSetAlbumSourcePaths()` — PUT mutation

All mutations should invalidate the relevant queries on success.

## Verification

```bash
cd src/image_vector_search/frontend && npx tsc --noEmit
# TypeScript compilation should succeed with no errors
```
