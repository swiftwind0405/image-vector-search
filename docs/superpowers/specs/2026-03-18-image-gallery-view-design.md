# Image Gallery View & Tag/Category Filter — Design Spec

**Date:** 2026-03-18
**Status:** Approved

## Overview

Add a gallery (grid) view mode to the Images admin page, alongside inline tag/category filter chips and a modal lightbox for per-image editing. The default list view is unchanged; users toggle between modes.

## Goals

1. Make image tagging/classification more intuitive by showing thumbnails.
2. Allow filtering images by tag and/or category to find relevant subsets quickly.
3. Preserve existing bulk-ops workflow in list mode.

## UI Layout

### Toolbar (unchanged + new)

The existing toolbar row gains a **List / Gallery toggle** on the right side. The folder dropdown stays on the left, coexisting with the new filters.

```
[Folder: All ▾]  |  247 images           [≡ List]  [⊞ Gallery]
```

### Inline Filter Bar (new, appears below toolbar in both modes)

A horizontal chip bar with all available tags and categories. Active filters are highlighted; inactive ones appear as dashed "+ add" chips. A "Clear all" link on the right resets filters.

```
Tags: [nature ✕] [travel ✕] [+ portrait] [+ food]  │  Category: [Travel ✕] [+ Work]   Clear all
```

Filter logic is **AND**: only images that satisfy ALL active tag chips AND whose category matches (or descends from) ALL active category chips are shown.

Category matching is **inclusive of descendants**: selecting "Travel" shows images assigned to Travel, Travel/Japan, Travel/Europe, etc.

### Gallery Mode (new)

- **6-column grid** of image cards (~120 px thumbnail height).
- Each card: thumbnail image, truncated filename below, tag badges.
- Thumbnails are served from a new backend endpoint: `GET /api/images/{hash}/thumbnail`.
- Clicking a card opens the **modal**.
- Result count shown below the grid: "Showing N of M matching images (filters…)".

### List Mode (unchanged)

Existing table view. Filter bar above still applies; the table rows are filtered client-side (or via API query param). Thumbnails are NOT added to list rows — keep it compact.

### Modal (new)

Opens when a gallery card is clicked. Contains:

- **Left panel**: full-resolution image display (constrained to viewport, object-fit contain).
- **Right panel**:
  - File path and truncated content hash.
  - `ImageTagEditor` (reuse existing component) for tags and categories.
  - "Open File" and "Reveal" action buttons.
  - "◀ Prev" / "Next ▶" buttons to navigate within the current filtered set.

The modal closes on Escape or clicking the backdrop.

## Backend Changes

### Thumbnail Endpoint

```
GET /api/images/{content_hash}/thumbnail?size=120
```

- Reads the image file from `canonical_path` via `MetadataRepository`.
- Resizes to fit within `size × size` (default 120, min 50, max 500) preserving aspect ratio using Pillow.
- Returns `Content-Type: image/jpeg` (quality 75) with `Cache-Control: max-age=86400`.
- Returns 404 JSON `{"detail": "not found"}` if the image record doesn't exist or the file is missing on disk.

### Extend `GET /api/images` response

`ImageRecord` currently has no tag/category data. Add an `ImageRecordWithLabels` type (extends `ImageRecord`) that includes:

```ts
tags: Tag[];        // all tags assigned to this image
categories: Category[];  // all categories assigned to this image
```

The backend `GET /api/images` route is updated to join tags and categories for each image in a single query (same join pattern already used by the `SearchResult` response). The Python domain model gets a parallel `ImageRecordWithLabels` dataclass.

This replaces the per-image `useImageTags(hash)` / `useImageCategories(hash)` fetches for the Images page. The `useImages()` hook return type changes from `ImageRecord[]` to `ImageRecordWithLabels[]`.

## Frontend Changes

### `ImagesPage` component

- Add `viewMode: 'list' | 'gallery'` state (default `'list'`), persisted to `localStorage`.
- Add `activeTags: string[]` and `activeCategoryId: number | null` state.
- Render `FilterBar` component below toolbar in both modes.
- Conditionally render `GalleryGrid` or existing table based on `viewMode`.
- Pass filtered image list (or query params) to both views.

### New components

| Component | Responsibility |
|---|---|
| `FilterBar` | Renders tag chips and category chips. Calls `onTagToggle` / `onCategoryToggle` / `onClear` callbacks. |
| `GalleryGrid` | Renders 6-column grid of `GalleryCard` components. |
| `GalleryCard` | Shows thumbnail via `<img src="/api/images/{hash}/thumbnail">`, filename, tag badges. Calls `onOpen` on click. |
| `ImageModal` | Full-screen modal with image + `ImageTagEditor` + prev/next nav. Uses existing `Dialog` primitive. |

### Data flow

1. `ImagesPage` fetches all images via `useImages()`, now returning `ImageRecordWithLabels[]` (tags + categories included per record).
2. Available tag names for the filter bar chips come from the existing `useTags()` hook.
3. Available categories for the filter bar chips come from the existing `useCategories()` hook (returns `CategoryNode[]` tree).
4. A `getDescendantIds(tree: CategoryNode[], categoryId: number): number[]` utility in `src/utils/categories.ts` recursively collects a node's ID and all descendant IDs.
5. Client-side AND-filter: an image passes if:
   - It has **all** active tag names in its `tags` array, AND
   - (if a category filter is active) at least one of its `categories` IDs is in the descendant set of the selected category.
   - Tags and category filters are AND-ed together.
6. `GalleryGrid` receives the filtered `ImageRecordWithLabels[]`; thumbnails fetched lazily by each `GalleryCard` `<img>` tag.

The `ImageTagEditor` component (used inside the modal) continues to use its own per-image fetch hooks — no change needed there.

## Error & Edge Cases

- **Missing file**: thumbnail endpoint returns 404; `GalleryCard` shows a 120×90 grey `#1a2233` placeholder with a broken-image icon centred.
- **No filters active**: show all images (same as current behaviour).
- **No results**: show "No images match the active filters." message centred below the filter bar.
- **Large library**: gallery renders all cards (no virtual scroll in v1); can be added later if perf is an issue.
- **Filter changed while modal is open**: modal closes, navigation index resets to the new filtered set.
- **Bulk operations on filtered set**: out of scope for this feature. Bulk ops continue to work on explicitly checkbox-selected images in list mode only.

## Testing

- Unit test: thumbnail endpoint — happy path (200 JPEG), missing DB record (404), file on disk deleted (404), `size` out of bounds (422).
- Unit test: `FilterBar` — toggle on/off, clear all.
- Unit test: `getDescendantIds` — leaf node, parent with children, non-existent ID.
- Unit test: AND-filter logic — tag-only filter, category-only filter, combined filter, no filters.
- Unit test: `GET /api/images` returns tags and categories per record.
- Integration test: thumbnail endpoint with a real temp JPEG/PNG file.
