# Admin Tag/Category Image Detail Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dedicated admin image detail pages for tags and categories, backed by filtered `/api/images` queries, while refactoring the existing image browser into shared frontend components.

**Architecture:** Extend the existing image listing backend to accept optional tag/category filters and descendant category expansion, then reuse one shared browser component across `Images`, tag detail, and category detail routes. Keep the response shape unchanged so gallery/list UI can be moved rather than rewritten.

**Tech Stack:** FastAPI, Pydantic, SQLite repository layer, React, TypeScript, TanStack Query, Vitest, pytest

---

### Task 1: Add backend integration tests for filtered image listing

**Files:**
- Modify: `tests/integration/test_tag_api.py`
- Test: `tests/integration/test_tag_api.py`

**Step 1: Write the failing test**

Add tests covering:

- `GET /api/images?tag_id=<id>` returns only images with that tag
- `GET /api/images?category_id=<id>` returns images in that category
- `GET /api/images?category_id=<id>` includes descendant category images
- `GET /api/images?tag_id=<id>&folder=<folder>` composes both filters

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_tag_api.py -k "api_images" -v`
Expected: FAIL because `/api/images` does not accept or apply the new filters yet.

**Step 3: Write minimal implementation**

Modify:

- `src/image_search_mcp/web/routes.py`
- `src/image_search_mcp/services/status.py`
- `src/image_search_mcp/repositories/sqlite.py`

Add optional filter params and apply them before returning labeled image records.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_tag_api.py -k "api_images" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_tag_api.py src/image_search_mcp/web/routes.py src/image_search_mcp/services/status.py src/image_search_mcp/repositories/sqlite.py
git commit -m "feat: support filtered image listing"
```

### Task 2: Add frontend API coverage for scoped image queries

**Files:**
- Modify: `src/image_search_mcp/web/src/api/images.ts`
- Create or Modify: `src/image_search_mcp/web/src/test/images-api.test.ts`
- Test: `src/image_search_mcp/web/src/test/images-api.test.ts`

**Step 1: Write the failing test**

Add tests that the image query hook builds the expected request URLs for:

- base images query
- tag scoped query
- category scoped query with descendant flag
- combined folder + route scope query

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/images-api.test.ts`
Expected: FAIL because the current hook only supports `folder`.

**Step 3: Write minimal implementation**

Extend the image query hook to accept an options object rather than only `folder`.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/images-api.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_search_mcp/web/src/api/images.ts src/image_search_mcp/web/src/test/images-api.test.ts
git commit -m "feat: add scoped image query hook"
```

### Task 3: Extract shared image browser UI from Images page

**Files:**
- Create: `src/image_search_mcp/web/src/components/ImageBrowser.tsx`
- Modify: `src/image_search_mcp/web/src/pages/ImagesPage.tsx`
- Test: `src/image_search_mcp/web/src/test/FilterBar.test.tsx`

**Step 1: Write the failing test**

Add a component-level test proving the extracted browser renders:

- provided title
- image counts
- existing list/gallery controls
- local filter behavior over supplied image data

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/FilterBar.test.tsx`
Expected: FAIL because the shared browser component does not exist yet.

**Step 3: Write minimal implementation**

Move the view-state-heavy browser content out of `ImagesPage.tsx` into `ImageBrowser.tsx`, keeping existing behavior unchanged.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/FilterBar.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_search_mcp/web/src/components/ImageBrowser.tsx src/image_search_mcp/web/src/pages/ImagesPage.tsx src/image_search_mcp/web/src/test/FilterBar.test.tsx
git commit -m "refactor: extract shared image browser"
```

### Task 4: Add tag and category image detail routes and pages

**Files:**
- Create: `src/image_search_mcp/web/src/pages/TagImagesPage.tsx`
- Create: `src/image_search_mcp/web/src/pages/CategoryImagesPage.tsx`
- Modify: `src/image_search_mcp/web/src/App.tsx`
- Modify: `src/image_search_mcp/web/src/pages/TagsPage.tsx`
- Modify: `src/image_search_mcp/web/src/pages/CategoriesPage.tsx`
- Possibly Modify: `src/image_search_mcp/web/src/components/CategoryTree.tsx`
- Test: `src/image_search_mcp/web/src/test/categories.test.ts`

**Step 1: Write the failing test**

Add tests that:

- tag management page links into a tag image detail page
- category management page links into a category image detail page
- category image detail page label indicates descendant inclusion

**Step 2: Run test to verify it fails**

Run: `npm test -- src/test/categories.test.ts`
Expected: FAIL because the routes and links do not exist yet.

**Step 3: Write minimal implementation**

Create two route pages that load metadata, request scoped images, and render the shared browser with route-specific titles and empty/error states.

**Step 4: Run test to verify it passes**

Run: `npm test -- src/test/categories.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_search_mcp/web/src/pages/TagImagesPage.tsx src/image_search_mcp/web/src/pages/CategoryImagesPage.tsx src/image_search_mcp/web/src/App.tsx src/image_search_mcp/web/src/pages/TagsPage.tsx src/image_search_mcp/web/src/pages/CategoriesPage.tsx src/image_search_mcp/web/src/components/CategoryTree.tsx src/image_search_mcp/web/src/test/categories.test.ts
git commit -m "feat: add tag and category image detail pages"
```

### Task 5: Run focused verification

**Files:**
- No code changes required unless failures are found

**Step 1: Run backend tests**

Run: `pytest tests/integration/test_tag_api.py -v`
Expected: PASS

**Step 2: Run frontend tests**

Run: `npm test -- src/test/images-api.test.ts src/test/categories.test.ts src/test/FilterBar.test.tsx`
Expected: PASS

**Step 3: Run targeted regression test**

Run: `pytest tests/integration/test_app_bootstrap.py -v`
Expected: PASS

**Step 4: Commit final adjustments if needed**

```bash
git add <any changed files>
git commit -m "test: verify admin image detail flows"
```
