# Task 009: Frontend Pages and Routing

**type**: impl
**depends-on**: [008-frontend-api]

## Goal

Create the album listing page, album detail page, and wire routing and navigation.

## Files to Create

- `src/image_vector_search/frontend/src/pages/AlbumsPage.tsx` — Album listing page
- `src/image_vector_search/frontend/src/pages/AlbumImagesPage.tsx` — Album detail page

## Files to Modify

- `src/image_vector_search/frontend/src/App.tsx` — Add `/albums` and `/albums/:albumId/images` routes
- `src/image_vector_search/frontend/src/components/Layout.tsx` — Add "Albums" nav item in sidebar

## What to Implement

### AlbumsPage.tsx

Grid of album cards showing:
- Cover image thumbnail (or placeholder for empty albums)
- Album name
- Type badge ("Manual" / "Smart")
- Image count
- Create album button opening a dialog/modal with:
  - Name input, description input
  - Type selector (manual/smart)
  - Rule logic selector (and/or) shown only when type is "smart"

Follow the visual and interaction patterns from `TagsPage.tsx`.

### AlbumImagesPage.tsx

Album detail page with:
- Header: album name, type badge, description, edit/delete buttons
- **For manual albums**: Image grid using `GalleryGrid`, add/remove image controls
- **For smart albums**: Rule editor section showing:
  - Current rules with tag name and include/exclude badge
  - AND/OR toggle
  - Add/remove rule controls
  - Source paths editor (list of folder paths with add/remove)
- Image grid (reuses `GalleryGrid`) showing matched images
- `ImageModal` for full-screen viewing (reuse existing component)
- Pagination (load more button or infinite scroll)

### Routing (`App.tsx`)

Add routes inside the authenticated layout:
```
/albums → AlbumsPage
/albums/:albumId/images → AlbumImagesPage
```

### Navigation (`Layout.tsx`)

Add "Albums" item to sidebar, positioned after Tags/Categories. Use an appropriate icon.

## Verification

```bash
cd src/image_vector_search/frontend && npx tsc --noEmit
# TypeScript compilation should succeed

cd src/image_vector_search/frontend && npm run build
# Build should succeed with no errors
```
