# Task 003 — Folders page (Green)

**type**: impl
**feature**: folders-page
**depends-on**: ["003-test", "002-impl"]

## Objective

Implement the `/folders` admin page, its API client, and its sidebar nav entry so that all Task 003 tests pass and the page works end-to-end against the real Task 002 backend. Reuse existing gallery and modal components — no new image rendering logic.

## Files

- **Create**:
  - `src/image_vector_search/frontend/src/api/folders.ts` — `useFolderBrowse(path)` React Query hook + TS types for `FolderBrowseResponse`.
  - `src/image_vector_search/frontend/src/pages/FoldersPage.tsx` — page component.
  - (Optional, inside FoldersPage or a sibling file) a small `FolderCard` component — keep it ≤ 30 lines, a `<Link>` wrapping a `Folder` icon + label.
- **Modify**:
  - `src/image_vector_search/frontend/src/App.tsx` — add `<Route path="folders" element={<FoldersPage />} />` inside the authenticated `<Layout />` branch.
  - `src/image_vector_search/frontend/src/components/Layout.tsx` — add `{ to: "/folders", icon: Folder, label: "Folders" }` to `navItems` (insert between Categories and Images) and a matching `pageMeta` entry with `title`, `subtitle`, `eyebrow` following the existing editorial style.
- **Read / imitate**:
  - `src/image_vector_search/frontend/src/pages/ImagesPage.tsx` and `components/ImageBrowser.tsx` for how the Images page wires `GalleryGrid` + `ImageModal`.
  - `src/image_vector_search/frontend/src/api/images.ts` for React Query key conventions and `apiFetch` usage.
  - `components/GalleryCard.tsx`, `GalleryGrid.tsx`, `ImageModal.tsx` — reuse as-is.
- **Do not touch**: backend, other pages, or existing API modules.

## BDD Scenarios

See Task 003 test for the full Gherkin. All six scenarios must pass after this task:

```gherkin
Scenario: Root page renders subfolder cards and direct images
Scenario: Clicking a subfolder drills down
Scenario: Breadcrumb navigation jumps back up the tree
Scenario: Image click opens the shared ImageModal
Scenario: Empty folder shows empty state
Scenario: Deep link loads the correct folder
```

## Steps

1. **API client** (`api/folders.ts`):
   - Define `FolderBrowseResponse { path: string; parent: string | null; folders: string[]; images: ImageRecord[]; next_cursor: string | null }` (reuse the existing `ImageRecord` type from `api/types.ts`).
   - Export `useFolderBrowse(path: string)` using `useQuery` with key `['folders', 'browse', path]` and fetch URL built via `URLSearchParams` (`/api/folders/browse?path=${encoded}`). Omit the `path` query param when `path === ""` to get the root view.
2. **Page** (`pages/FoldersPage.tsx`):
   - `useSearchParams()` → read `path` (default `""`).
   - Call `useFolderBrowse(path)`.
   - Render a loading skeleton matching the Images page idiom while `isLoading`.
   - Render an error fallback using `ErrorBoundary`'s existing patterns or a simple inline error for query `error`.
   - **Breadcrumbs**: split `path` by `/`, render `Root` first (`Link` to `/folders`), then accumulate segments into clickable `Link`s (`/folders?path=<acc>`). Active (last) segment is non-clickable text.
   - **Subfolders section**: hidden when `folders.length === 0`. Otherwise a section header `"Subfolders"` and a CSS grid of `FolderCard`s. Each card: `<Link to={`/folders?path=${encodeURIComponent(f)}`}>` containing a `Folder` lucide icon and the leaf segment (`f.split('/').pop()`), with the full path in `title=` for tooltip. Use the dark-curation styling tokens (border, bg, shadow classes) already used by other cards.
   - **Images section**: hidden when `images.length === 0`. Section header `"Images"` + reuse `GalleryGrid` (or whichever component `ImageBrowser` uses to render the thumbnail grid). Pass the `images` array directly. Use the same `ImageModal` opening mechanism the Images page uses (typically click handler → state → modal mounted at page level).
   - **Empty state**: when both arrays empty → `"This folder is empty."` in a muted-foreground card.
3. **Route** (`App.tsx`): add `<Route path="folders" element={<FoldersPage />} />` inside the authenticated `<Layout />` block. No guard changes needed.
4. **Nav** (`Layout.tsx`): insert the Folders entry in `navItems` and add its `pageMeta` entry. Icon: `Folder` from `lucide-react`.
5. **Run frontend tests**: `npm --prefix src/image_vector_search/frontend test -- FoldersPage`.
6. **Full frontend test sweep**: `npm --prefix src/image_vector_search/frontend test` — no regressions.
7. **Full backend suite**: `pytest` — ensure no backend regression (should be unaffected, but verify).
8. **Manual smoke** (required before marking complete):
   - Run dev server.
   - Open `/folders` in the browser, click a subfolder, verify URL updates and contents load.
   - Click an image, verify `ImageModal` opens.
   - Click a breadcrumb and verify navigation.
   - Verify browser back/forward works at least two levels deep.

## Verification

- `npm --prefix src/image_vector_search/frontend test -- FoldersPage` — all scenarios green.
- `npm --prefix src/image_vector_search/frontend test` — full frontend suite green.
- `pytest` — backend suite still green.
- Manual smoke checklist above complete.

## Out of scope

- Folder counts, cover thumbnails, recursive toggle, folder rename/delete (explicitly YAGNI per design).
- Bulk folder tagging UI (already exists via separate bulk endpoints).
- Any changes to `/api/folders`, `/api/images`, or their frontend clients.
