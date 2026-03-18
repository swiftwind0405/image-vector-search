# Admin Tag/Category Image Detail Design

**Context**

The admin web UI currently supports:

- `Images`: browse indexed images with folder filtering, local tag/category filtering, bulk operations, list/gallery views, modal preview, and per-image label editing.
- `Tags`: manage tag CRUD only.
- `Categories`: manage category tree CRUD only.

The missing capability is reverse lookup from `Tags` and `Categories` into the images assigned to them. The user chose a dedicated detail page approach rather than redirecting into the generic `Images` page.

**Goals**

- Clicking a tag opens an image detail page for that tag.
- Clicking a category opens an image detail page for that category.
- Category detail pages include images assigned to descendant categories.
- Detail pages retain the existing `Images` page capabilities, including filters and bulk operations.
- Frontend should reuse `Images` page elements as much as possible; if reuse is blocked, refactor `Images` into shared building blocks.

**Non-Goals**

- No change to MCP tools.
- No change to embedding or vector search behavior.
- No redesign of the existing admin layout.
- No new authorization model.

**Recommended Approach**

Combine two ideas:

1. Add dedicated detail routes:
   - `/tags/:tagId/images`
   - `/categories/:categoryId/images`
2. Extend the existing `/api/images` endpoint so all image-list pages use one filtered backend query surface.

This keeps the API simple and prevents near-duplicate endpoints like `/api/tags/{id}/images` and `/api/categories/{id}/images`, while still giving the UI separate pages with their own titles and context.

**Backend Design**

Extend `GET /api/images` with optional query params:

- `folder: str | None`
- `tag_id: int | None`
- `category_id: int | None`
- `include_descendants: bool = True`

Behavior:

- No extra filters: current behavior, all active images.
- `tag_id`: return active images associated with that tag.
- `category_id`: return active images associated with that category.
- `include_descendants=true`: for categories, include all descendants recursively.
- Filters are composable; for example a tag detail page can still apply a folder filter in the shared browser UI.

Service/repository changes:

- Add a single repository path that returns active images with labels under optional filters instead of forcing the frontend to fetch everything and filter locally.
- Reuse the existing tag/category association tables and the existing recursive category query logic.
- Keep output shape as `ImageRecordWithLabels[]` so the frontend gallery/list components remain unchanged.

Implementation note:

- The repository already exposes helpers like `filter_by_tags()` and `filter_by_category()`. Those are sufficient to build filtered image queries without schema changes.
- The minimal safe refactor is to extend `StatusService.list_active_images_with_labels()` and `MetadataRepository.list_active_images_with_labels()` with optional filtering arguments.

**Frontend Design**

Extract the current reusable image browsing experience from `ImagesPage.tsx` into a shared page-level component, for example `ImageBrowser`.

Responsibilities:

- Shared browser component:
  - folder selector
  - folder bulk actions
  - selection state
  - bulk tag/category actions
  - view mode toggle
  - local filter bar
  - pagination
  - list/gallery rendering
  - image modal
  - per-image tag/category editor
- Route pages:
  - `ImagesPage`: loads unscoped images and renders shared browser with title `Images`
  - `TagImagesPage`: loads tag metadata and scoped images, renders title like `Tag: sunset`
  - `CategoryImagesPage`: loads category metadata and scoped images, renders title like `Category: nature`

Scope model:

- Route-level scope is locked and comes from the route param (`tag_id` or `category_id`).
- Existing local filter bar remains available for extra narrowing.
- Existing bulk operations remain available.
- Existing folder actions remain available.

Navigation:

- `TagsPage`: tag name becomes a link/button to the tag image detail page.
- `CategoriesPage`: each category row/node gets a `View Images` affordance to open the category image detail page.

**Why This Design**

Compared with redirecting into the generic `Images` page, dedicated detail routes preserve admin context and make deep links stable and obvious.

Compared with duplicating the page three times, extracting a shared browser prevents immediate code drift. The current `ImagesPage` already contains enough behavior that duplication would become expensive quickly.

Compared with new dedicated backend endpoints per entity, extending `/api/images` keeps the contract flatter and easier to evolve.

**Error Handling**

- Unknown tag/category id on detail pages should produce a clear empty/error state, not a blank page.
- Backend should reject invalid query parameter values with normal FastAPI validation.
- Category detail pages should still work when the chosen category has no direct images but descendants do.

**Testing Strategy**

Backend:

- Add integration coverage for `/api/images?tag_id=...`.
- Add integration coverage for `/api/images?category_id=...`.
- Add integration coverage that category filtering includes descendants.
- Add integration coverage that folder + tag/category filters compose correctly.

Frontend:

- Add API hook tests or component tests for scoped image fetching query strings.
- Add page tests proving tag/category detail pages render scoped images.
- Add tests that existing `ImagesPage` behavior remains intact after extraction.

**Risks**

- `ImagesPage.tsx` is currently monolithic, so refactoring must preserve selection, pagination, and dialog state.
- If route pages fetch metadata and images independently, loading and missing-id states need to be handled explicitly.
- Client-side local filters must layer on top of already scoped server results without confusing counts.

**Acceptance Criteria**

- From `Tags`, an admin can open a dedicated image page for a tag.
- From `Categories`, an admin can open a dedicated image page for a category.
- Category detail pages include descendant category images.
- Detail pages preserve current image browsing controls.
- Shared UI logic is extracted so `ImagesPage` is not left as a separate divergent implementation.
