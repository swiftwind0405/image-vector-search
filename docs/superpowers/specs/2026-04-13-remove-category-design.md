# Remove Category Feature — Design

**Date:** 2026-04-13
**Status:** Approved for implementation

## Background

The project currently has four orthogonal organization concepts:

- **Folder structure** — hierarchical, tied to on-disk layout, browse-only.
- **Tag** — flat labels, many-to-many, used for filtering and search.
- **Album** — user-defined collections, either manual or smart (driven by tag rules).
- **Category** — hierarchical logical labels (tree), many-to-many, independent of disk layout.

Category's only unique capability is "hierarchical logical classification decoupled from the filesystem." In practice, the folder tree already expresses the user's taxonomy, and multi-dimensional grouping is served by flat tags plus smart albums. Category has become a redundant concept that adds schema complexity, UI surface, and API weight without earning its keep.

## Goal

Completely remove the Category concept from the project. Going forward, users rely on folders + tags + albums. No replacement feature is introduced.

## Non-Goals

- No data migration. Existing category rows and `image_tags.category_id` assignments are discarded (explicit user decision).
- No "soft delete" or JSON export of existing category data.
- No unrelated refactoring of neighboring code.
- No new feature to replace what Category did.

## Scope

Removal touches every layer of the stack. The changes are wide but mechanical.

### 1. Database schema (`repositories/schema.sql`)

- Delete the `categories` table definition.
- Redefine `image_tags` without the `category_id` column, the `(tag_id XOR category_id)` CHECK constraint, or the `UNIQUE(content_hash, category_id)` constraint. New shape:
  ```sql
  CREATE TABLE image_tags (
    content_hash TEXT NOT NULL,
    tag_id       INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at   TEXT NOT NULL,
    PRIMARY KEY (content_hash, tag_id)
  );
  CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
  ```
- Delete the `idx_image_tags_category_id` index.

### 2. Startup migration (`repositories/sqlite.py`)

Follow the existing idempotent `_ensure_*` pattern. Add `_drop_category_schema(connection)` invoked at startup alongside the other ensure methods. Steps, executed in a single transaction:

1. Skip entirely if `categories` table does not exist (idempotent no-op on second run and fresh installs).
2. Rebuild `image_tags` via the classic SQLite rewrite (old SQLite versions cannot `DROP COLUMN`):
   ```sql
   CREATE TABLE image_tags__new (
     content_hash TEXT NOT NULL,
     tag_id       INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
     created_at   TEXT NOT NULL,
     PRIMARY KEY (content_hash, tag_id)
   );
   INSERT INTO image_tags__new (content_hash, tag_id, created_at)
     SELECT content_hash, tag_id, created_at
       FROM image_tags
      WHERE tag_id IS NOT NULL;
   DROP TABLE image_tags;
   ALTER TABLE image_tags__new RENAME TO image_tags;
   CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
   ```
3. `DROP TABLE categories;`
4. Drop any lingering `idx_image_tags_category_id` index.

Rows where `tag_id IS NULL` (i.e., category-only associations) are dropped. That is the expected data loss.

### 3. Domain models (`domain/models.py`)

- Delete `Category` and `CategoryNode` classes.
- Remove `categories: list[Category]` from `SearchResult` and `ImageRecordWithLabels`.

### 4. Repository layer (`repositories/sqlite.py`)

- Delete all category CRUD methods: create/rename/delete/move/list/tree, add/remove image associations, bulk operations.
- Strip category JOINs from any image-fetching query that currently returns categories alongside tags.

### 5. Service layer

- `services/tagging.py`: remove category-related methods and code paths.
- `services/search.py`: remove category hydration from search results.
- `services/status.py`: remove category counts if surfaced.

### 6. HTTP API

- `api/admin_tag_routes.py`: delete all `/categories*` endpoints and any `image/{hash}/categories` endpoints.
- `api/admin_bulk_routes.py`: delete category-related bulk actions.
- `api/admin_routes.py`: scan for and remove any remaining references.

### 7. MCP tools (`tools/`)

- Delete the `manage_categories` tool entirely (`tools/tag_tools.py`).
- From the image-tagging tool, remove the `add_category`, `remove_category`, and `list_categories` action branches and the `category_id` parameter.
- `tools/image_tools.py`: remove any category hooks.

### 8. Frontend

Delete wholesale:

- `frontend/src/pages/CategoriesPage.tsx`
- `frontend/src/pages/CategoryImagesPage.tsx`
- `frontend/src/components/CategoryTree.tsx`
- `frontend/src/components/CategorySelect.tsx`
- `frontend/src/api/categories.ts`
- `frontend/src/utils/categories.ts`
- Corresponding test files (`categories.test.ts`, `TagCategorySelect.test.tsx`, etc.)

Edit in place to remove category sections:

- `frontend/src/App.tsx` — drop category routes.
- `frontend/src/components/Layout.tsx` — drop category nav entry (both desktop and mobile drawer).
- `frontend/src/components/ImageTagEditor.tsx` — remove category picker block.
- `frontend/src/components/FilterBar.tsx` — remove category filter controls.
- `frontend/src/components/ImageBrowser.tsx` — remove category badges and filter state.
- `frontend/src/api/types.ts` — remove `Category`, `CategoryNode` types and drop `categories` fields from image types.
- `frontend/src/api/images.ts` / `bulk.ts` — drop category parameters.

### 9. Tests

- Delete: `tests/unit/test_*category*` (if present), category-specific integration tests in `tests/integration/test_tag_api.py` and `tests/integration/test_bulk_api.py`, `frontend/src/test/categories.test.ts`, `frontend/src/test/TagCategorySelect.test.tsx`.
- Edit: remove category assertions and fixtures from `test_domain_models.py`, `test_sqlite_repository.py`, `test_search_service.py`, `test_tag_service.py`, `test_bulk_service.py`, `test_bulk_repository.py`, `test_tag_tools.py`, `test_index_tools.py`, `test_web_admin.py`, `test_app_bootstrap.py`, `ImagesPage.test.tsx`, `FoldersPage.test.tsx`, `images-api.test.ts`, `filter.test.ts`, `admin-navigation.test.tsx`, `FilterBar.test.tsx`.
- Add: one unit test for the new `_drop_category_schema` migration — run it against a fixture DB populated with categories and category-only `image_tags` rows, then assert (a) `categories` table is gone, (b) `image_tags` has no `category_id` column, (c) tag-only associations survived, (d) a second invocation is a safe no-op.

### 10. Documentation

- `docs/usage.md`: remove the Category section.
- `docs/api.md`: remove Category endpoints from the reference.

## Risks & Mitigations

- **Data loss is intentional.** User explicitly chose option C (discard). Nothing to mitigate.
- **Migration idempotency.** The `_drop_category_schema` method must be a safe no-op on already-migrated and fresh-install databases. Covered by the dedicated unit test above.
- **Wide blast radius.** 50+ files touch categories. Mitigated by walking the layers top-down (schema → repo → service → API → tools → frontend → tests → docs) and running `pytest` plus `npm run test` / `tsc` after each layer.
- **Missed reference.** After the sweep, a project-wide `grep -i "categor"` must return zero matches outside of historical docs under `docs/plans/`. Historical design docs under `docs/plans/` are left untouched — they describe past decisions and should not be rewritten.

## Success Criteria

1. Fresh-install DB boots with the new schema; no `categories` table is created.
2. Existing DB (with category data) boots, migration runs once, `categories` table is dropped, tag-only associations preserved, second boot is a no-op.
3. Backend test suite passes with zero references to `Category`/`categories` in production code.
4. Frontend builds and test suite passes; no category UI remains.
5. MCP tool catalogue no longer lists `manage_categories`; `image_tools` tag action list no longer advertises `add_category`/`remove_category`/`list_categories`.
6. `docs/usage.md` and `docs/api.md` describe only folder + tag + album organization.
