# Remove Category Feature — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Category concept from every layer of the project (schema, repo, services, API, MCP tools, frontend, docs). Existing category data is discarded. Spec: `docs/superpowers/specs/2026-04-13-remove-category-design.md`.

**Architecture:** Peel the feature off top-down so the tree stays buildable after every task. Each task removes one layer (frontend → MCP tools → HTTP API → services → repo → domain → schema → docs) and updates the tests that touch that layer in the same commit. The schema task adds an idempotent startup migration that drops the `categories` table and rebuilds `image_tags` without the `category_id` column.

**Tech Stack:** Python 3.12, FastAPI, SQLite, pytest, React + Vite, TypeScript, Vitest.

**Verification cheat sheet** (run after every task):

```bash
# Backend
pytest -x
# Frontend
cd src/image_vector_search/frontend && npm run test -- --run && npx tsc --noEmit
# Residual reference sweep (run after Task 10)
grep -rni "categor" src/ tests/ docs/usage.md docs/api.md
```

---

## File Structure

**Backend files modified**
- `src/image_vector_search/repositories/schema.sql` — schema (Task 8)
- `src/image_vector_search/repositories/sqlite.py` — repo methods + startup migration (Tasks 6, 8)
- `src/image_vector_search/domain/models.py` — Category/CategoryNode classes (Task 7)
- `src/image_vector_search/services/tagging.py` — category methods (Task 5)
- `src/image_vector_search/services/search.py` — category filter branch (Task 5)
- `src/image_vector_search/services/status.py` — category counts if any (Task 5)
- `src/image_vector_search/api/admin_tag_routes.py` — category endpoints (Task 3)
- `src/image_vector_search/api/admin_bulk_routes.py` — bulk category endpoints (Task 3)
- `src/image_vector_search/api/admin_routes.py` — residual category refs (Task 3)
- `src/image_vector_search/tools/tag_tools.py` — `manage_categories` MCP tool, category actions (Task 2)
- `src/image_vector_search/tools/image_tools.py` — residual category refs (Task 2)

**Frontend files deleted**
- `src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`
- `src/image_vector_search/frontend/src/pages/CategoryImagesPage.tsx`
- `src/image_vector_search/frontend/src/components/CategoryTree.tsx`
- `src/image_vector_search/frontend/src/components/CategorySelect.tsx`
- `src/image_vector_search/frontend/src/api/categories.ts`
- `src/image_vector_search/frontend/src/utils/categories.ts`
- `src/image_vector_search/frontend/src/test/categories.test.ts`
- `src/image_vector_search/frontend/src/test/TagCategorySelect.test.tsx`

**Frontend files modified**
- `src/image_vector_search/frontend/src/App.tsx` — routes (Task 1)
- `src/image_vector_search/frontend/src/components/Layout.tsx` — nav item + page chrome entry (Task 1)
- `src/image_vector_search/frontend/src/api/types.ts` — Category types and fields (Task 1)
- `src/image_vector_search/frontend/src/api/images.ts` / `bulk.ts` — category params (Task 1)
- `src/image_vector_search/frontend/src/components/ImageTagEditor.tsx` — category block (Task 1)
- `src/image_vector_search/frontend/src/components/FilterBar.tsx` — category filter (Task 1)
- `src/image_vector_search/frontend/src/components/ImageBrowser.tsx` — category badges (Task 1)
- Test files that still assert on categories (Tasks 1, 3, 4, 5, 6, 7)

**Docs**
- `docs/usage.md`, `docs/api.md` — Task 10

---

## Task Ordering Rationale

- **Tasks 1–3 (frontend, MCP tools, HTTP API)** are the public-facing surfaces. Removing them first means nothing can reach category code anymore.
- **Tasks 4–5 (bulk repo/service, tagging/search services)** strip the service layer once there are no callers.
- **Tasks 6–7 (repo, domain models)** remove the type definitions and storage code.
- **Task 8 (schema + startup migration + migration unit test)** lands the DB change after all Python code has stopped reading `category_id`.
- **Task 9 (cross-cutting test cleanup)** mops up any category assertions that leaked past per-layer cleanups.
- **Task 10 (docs)** updates user-facing documentation and runs the final grep sweep.

---

## Task 1: Remove Frontend Category UI

**Files:**
- Delete: `src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`
- Delete: `src/image_vector_search/frontend/src/pages/CategoryImagesPage.tsx`
- Delete: `src/image_vector_search/frontend/src/components/CategoryTree.tsx`
- Delete: `src/image_vector_search/frontend/src/components/CategorySelect.tsx`
- Delete: `src/image_vector_search/frontend/src/api/categories.ts`
- Delete: `src/image_vector_search/frontend/src/utils/categories.ts`
- Delete: `src/image_vector_search/frontend/src/test/categories.test.ts`
- Delete: `src/image_vector_search/frontend/src/test/TagCategorySelect.test.tsx`
- Modify: `src/image_vector_search/frontend/src/App.tsx`
- Modify: `src/image_vector_search/frontend/src/components/Layout.tsx`
- Modify: `src/image_vector_search/frontend/src/api/types.ts`
- Modify: `src/image_vector_search/frontend/src/api/images.ts`
- Modify: `src/image_vector_search/frontend/src/api/bulk.ts`
- Modify: `src/image_vector_search/frontend/src/components/ImageTagEditor.tsx`
- Modify: `src/image_vector_search/frontend/src/components/FilterBar.tsx`
- Modify: `src/image_vector_search/frontend/src/components/ImageBrowser.tsx`
- Modify tests: `src/image_vector_search/frontend/src/test/{ImagesPage,FoldersPage,images-api,filter,admin-navigation,FilterBar}.test.{ts,tsx}`

- [ ] **Step 1: Delete standalone category files**

```bash
cd src/image_vector_search/frontend
git rm src/pages/CategoriesPage.tsx \
       src/pages/CategoryImagesPage.tsx \
       src/components/CategoryTree.tsx \
       src/components/CategorySelect.tsx \
       src/api/categories.ts \
       src/utils/categories.ts \
       src/test/categories.test.ts \
       src/test/TagCategorySelect.test.tsx
```

- [ ] **Step 2: Update `src/App.tsx` — drop category imports and routes**

Remove imports (currently lines 5, 11):

```tsx
import CategoriesPage from "./pages/CategoriesPage";
import CategoryImagesPage from "./pages/CategoryImagesPage";
```

Remove routes (currently lines 38–39):

```tsx
<Route path="categories" element={<CategoriesPage />} />
<Route path="categories/:categoryId/images" element={<CategoryImagesPage />} />
```

- [ ] **Step 3: Update `src/components/Layout.tsx` — drop nav item and page chrome**

In the `navItems` array, remove the entry:

```tsx
{ to: "/categories", icon: FolderTree, label: "Categories" },
```

Also remove the `FolderTree` import from `lucide-react` if no longer referenced.

In the page-chrome array (the one containing `title: "Category Structure"`), remove the whole object:

```tsx
{
  match: (pathname: string) => pathname.startsWith("/categories"),
  title: "Category Structure",
  subtitle: "Shape the hierarchy that organizes the archive and inspect each branch visually.",
  eyebrow: "Taxonomy",
},
```

- [ ] **Step 4: Update `src/api/types.ts` — drop category types**

Remove any `Category` and `CategoryNode` interface/type declarations. From image-record types, remove the `categories?: Category[]` (or similarly named) field. If anything imports `Category` / `CategoryNode`, remove those imports in the consumer files.

- [ ] **Step 5: Update `src/api/images.ts` and `src/api/bulk.ts` — drop category params**

Remove any query parameters, request body fields, or helper functions with `category_id` / `category_ids` / `category`. Remove imports of `Category` types.

- [ ] **Step 6: Update `src/components/ImageTagEditor.tsx`**

Remove the block that renders category pickers and the state/props that drive it. Keep the tag editor working exactly as before for tags.

- [ ] **Step 7: Update `src/components/FilterBar.tsx`**

Remove the category filter control, related local state, and any `category_id` URL param handling. Keep tag filter and folder filter intact.

- [ ] **Step 8: Update `src/components/ImageBrowser.tsx`**

Remove category badges from the image card and any category-related props.

- [ ] **Step 9: Update affected test files**

In each of the following test files, delete any test that exercises categories and strip category assertions from shared fixtures:

- `src/test/ImagesPage.test.tsx`
- `src/test/FoldersPage.test.tsx`
- `src/test/images-api.test.ts`
- `src/test/filter.test.ts`
- `src/test/admin-navigation.test.tsx`
- `src/test/FilterBar.test.tsx`

Use `git grep -l -i categor src/test/` to find every remaining reference inside the frontend test tree; the grep must return an empty list before moving on.

- [ ] **Step 10: Typecheck + test**

```bash
cd src/image_vector_search/frontend
npx tsc --noEmit
npm run test -- --run
```

Expected: both succeed with zero errors.

- [ ] **Step 11: Grep-verify no category references remain in frontend**

```bash
git grep -n -i "categor" src/image_vector_search/frontend/src
```

Expected: empty output.

- [ ] **Step 12: Commit**

```bash
git add -A src/image_vector_search/frontend
git commit -m "refactor(frontend): remove Category UI, routes, API client, and types"
```

---

## Task 2: Remove Category from MCP Tools

**Files:**
- Modify: `src/image_vector_search/tools/tag_tools.py`
- Modify: `src/image_vector_search/tools/image_tools.py`
- Modify: `tests/unit/test_tag_tools.py`
- Modify: `tests/unit/test_index_tools.py`

- [ ] **Step 1: Delete the `manage_categories` tool from `tools/tag_tools.py`**

Remove the entire `@tool(name="manage_categories", …)` decorator and its `async def manage_categories(...)` body (currently starting around line 45). Also remove `manage_categories` from any tool-registration list or `__all__` export in the same file.

- [ ] **Step 2: Strip category actions from the image-tagging tool in `tools/tag_tools.py`**

The image-tagging tool currently supports `add_category`, `remove_category`, and `list_categories` actions plus a `category_id` parameter. Remove:

- `"add_category"`, `"remove_category"`, and `"list_categories"` from the action `Literal[...]` type / allowed set.
- The `category_id: int | None = None` parameter from the function signature.
- Every `if action == "add_category"` / `remove_category` / `list_categories` branch.
- Any helper `getattr(svc, "add_category_to_image", …)` / `remove_category_from_image` lookups.

Update the tool `description` string to mention tags only.

- [ ] **Step 3: Update `tools/image_tools.py`**

Remove any category imports, parameters, or response fields. Use:

```bash
grep -n -i category src/image_vector_search/tools/image_tools.py
```

Expected after edits: empty.

- [ ] **Step 4: Update `tests/unit/test_tag_tools.py`**

Delete every test that calls `manage_categories` or exercises `add_category` / `remove_category` / `list_categories`. Delete fixtures that create a `TagService` with category-capable stubs.

- [ ] **Step 5: Update `tests/unit/test_index_tools.py`**

Remove any category assertions or fixtures. Run `grep -n -i category tests/unit/test_index_tools.py`; expected empty.

- [ ] **Step 6: Run affected tests**

```bash
pytest tests/unit/test_tag_tools.py tests/unit/test_index_tools.py -v
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/image_vector_search/tools tests/unit/test_tag_tools.py tests/unit/test_index_tools.py
git commit -m "refactor(tools): drop manage_categories MCP tool and category actions"
```

---

## Task 3: Remove Category HTTP Endpoints

**Files:**
- Modify: `src/image_vector_search/api/admin_tag_routes.py`
- Modify: `src/image_vector_search/api/admin_bulk_routes.py`
- Modify: `src/image_vector_search/api/admin_routes.py`
- Modify: `tests/integration/test_tag_api.py`
- Modify: `tests/integration/test_bulk_api.py`
- Modify: `tests/integration/test_web_admin.py`
- Modify: `tests/integration/test_app_bootstrap.py`

- [ ] **Step 1: Edit `api/admin_tag_routes.py`**

Delete these pydantic request models (currently lines 16–23, 28–29, 34–35):

```python
class CreateCategoryRequest(BaseModel): ...
class UpdateCategoryRequest(BaseModel): ...
class BatchDeleteCategoriesRequest(BaseModel): ...
class AddImageToCategoryRequest(BaseModel): ...
```

Delete every category route (the `# --- Categories ---` block and the three image/category association routes, currently lines 93–154 and 170–181):

- `POST /api/categories`
- `GET /api/categories`
- `GET /api/categories/export`
- `POST /api/categories/import`
- `GET /api/categories/{category_id}/children`
- `PUT /api/categories/{category_id}`
- `DELETE /api/categories/{category_id}`
- `POST /api/categories/batch-delete`
- `POST /api/images/{content_hash}/categories`
- `DELETE /api/images/{content_hash}/categories/{category_id}`
- `GET /api/images/{content_hash}/categories`

After editing, the only remaining section headers in the file should be `# --- Tags ---` and `# --- Image associations ---` (tags only).

- [ ] **Step 2: Edit `api/admin_bulk_routes.py`**

Delete request models `BulkCategoryRequest` and `FolderCategoryRequest`. Delete handlers `bulk_add_categories`, `bulk_remove_categories`, `bulk_folder_add_categories`, `bulk_folder_remove_categories` and their route decorators.

- [ ] **Step 3: Edit `api/admin_routes.py`**

```bash
grep -n -i category src/image_vector_search/api/admin_routes.py
```

Remove every line the grep surfaces. Expected after edits: empty grep.

- [ ] **Step 4: Update integration tests**

In `tests/integration/test_tag_api.py`, `test_bulk_api.py`, `test_web_admin.py`, `test_app_bootstrap.py`: delete every test function whose body posts/gets/deletes any `/api/categor…` URL, and strip category assertions from shared setup/fixtures. Run for each file:

```bash
grep -n -i categor tests/integration/test_tag_api.py
grep -n -i categor tests/integration/test_bulk_api.py
grep -n -i categor tests/integration/test_web_admin.py
grep -n -i categor tests/integration/test_app_bootstrap.py
```

Expected: all empty.

- [ ] **Step 5: Run the affected test modules**

```bash
pytest tests/integration/test_tag_api.py \
       tests/integration/test_bulk_api.py \
       tests/integration/test_web_admin.py \
       tests/integration/test_app_bootstrap.py -v
```

Expected: all pass. (They rely on service/repo methods that still exist at this point — those are removed in later tasks, so this ordering is important.)

- [ ] **Step 6: Commit**

```bash
git add src/image_vector_search/api tests/integration
git commit -m "refactor(api): remove category HTTP endpoints"
```

---

## Task 4: Remove Category from Bulk Service and Bulk Repository

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py` (bulk category methods only)
- Modify: `src/image_vector_search/services/` (any bulk service layer, likely inside `tagging.py`)
- Modify: `tests/unit/test_bulk_repository.py`
- Modify: `tests/unit/test_bulk_service.py`

- [ ] **Step 1: Remove bulk category methods from `sqlite.py`**

Delete these methods (grep to find exact line ranges):

```bash
grep -n "def bulk_add_category\|def bulk_remove_category\|def bulk_folder_add_category\|def bulk_folder_remove_category\|def bulk_delete_categories" src/image_vector_search/repositories/sqlite.py
```

Delete each method body in full. Do not touch `bulk_add_tag` / `bulk_remove_tag` / `bulk_folder_add_tag` / `bulk_folder_remove_tag` / `bulk_delete_tags` equivalents.

- [ ] **Step 2: Remove bulk category methods from `services/tagging.py`**

Delete `bulk_delete_categories`, `bulk_add_category`, `bulk_remove_category`, `bulk_folder_add_category`, `bulk_folder_remove_category` (currently lines ~71–141).

- [ ] **Step 3: Update `tests/unit/test_bulk_repository.py` and `test_bulk_service.py`**

Delete every test that calls a bulk category method. Strip category rows from shared fixtures. Run:

```bash
grep -n -i categor tests/unit/test_bulk_repository.py tests/unit/test_bulk_service.py
```

Expected: empty.

- [ ] **Step 4: Run affected tests**

```bash
pytest tests/unit/test_bulk_repository.py tests/unit/test_bulk_service.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/repositories/sqlite.py \
        src/image_vector_search/services/tagging.py \
        tests/unit/test_bulk_repository.py tests/unit/test_bulk_service.py
git commit -m "refactor(bulk): remove bulk category service and repository methods"
```

---

## Task 5: Remove Category from Tagging, Search, and Status Services

**Files:**
- Modify: `src/image_vector_search/services/tagging.py`
- Modify: `src/image_vector_search/services/search.py`
- Modify: `src/image_vector_search/services/status.py`
- Modify: `tests/unit/test_tag_service.py`
- Modify: `tests/unit/test_search_service.py`

- [ ] **Step 1: Edit `services/tagging.py`**

Remove the category imports at the top:

```python
from image_vector_search.domain.models import Tag, Category, CategoryNode
```

Becomes:

```python
from image_vector_search.domain.models import Tag
```

Delete every remaining category method: `create_category`, `list_categories`, `get_category_tree`, `rename_category`, `move_category`, `delete_category`, `add_image_to_category`, `remove_image_from_category`, `get_image_categories`, `export_categories_markdown`, `import_categories_markdown`, `_render_category_tree`, and any other helper surfaced by:

```bash
grep -n -i category src/image_vector_search/services/tagging.py
```

Expected after edits: empty grep.

- [ ] **Step 2: Edit `services/search.py`**

Remove the `category_id` parameter from every public method signature (currently lines 35, 82, 175). Remove the `category_id` branch of the filter assembly (currently lines 183–184 calling `self.repository.filter_by_category(...)`). Drop any `category_id` kwarg plumbed through to repository calls. After edits:

```bash
grep -n -i category src/image_vector_search/services/search.py
```

Expected: empty.

- [ ] **Step 3: Edit `services/status.py`**

```bash
grep -n -i category src/image_vector_search/services/status.py
```

Remove whatever the grep surfaces (typically a counts aggregate). Expected after edits: empty.

- [ ] **Step 4: Update unit tests**

Strip category tests and category fixtures from `tests/unit/test_tag_service.py` and `tests/unit/test_search_service.py`. Verify:

```bash
grep -n -i categor tests/unit/test_tag_service.py tests/unit/test_search_service.py
```

Expected: empty.

- [ ] **Step 5: Run affected tests**

```bash
pytest tests/unit/test_tag_service.py tests/unit/test_search_service.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/image_vector_search/services tests/unit/test_tag_service.py tests/unit/test_search_service.py
git commit -m "refactor(services): remove category methods from tagging, search, and status"
```

---

## Task 6: Remove Category from Repository Layer

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Modify: `tests/unit/test_sqlite_repository.py`

- [ ] **Step 1: Remove category imports from `sqlite.py`**

Find the imports block (currently lines 9–10):

```python
from image_vector_search.domain.models import (
    ...
    Category,
    CategoryNode,
    ...
)
```

Remove the `Category` and `CategoryNode` entries.

- [ ] **Step 2: Remove every remaining category method**

Delete (use grep to find exact positions):

- `create_category`
- `list_categories`
- `get_category_tree`
- `rename_category`
- `move_category`
- `delete_category`
- `add_image_to_category`
- `remove_image_from_category`
- `get_image_categories`
- `get_categories_for_images`
- `filter_by_category`
- `_row_to_category`

Also remove the `category_id: int | None = None` parameter from any internal helper (`_tag_row_insert`, `_insert_image_tag`, etc. — currently at lines 133, 145, 157, 169, 181, 192, 1312, 1323, 1357, and inside `filter_by_tags` around 1387–1421). In each case, also delete the `category_id` branch that composes the SQL.

Drop every SQL fragment that references `image_tags.category_id` or the `categories` table. Strip `category_id` from any `INSERT INTO image_tags` call — the new shape is `INSERT INTO image_tags (content_hash, tag_id, created_at) VALUES (?, ?, ?)`.

After edits:

```bash
grep -n -i category src/image_vector_search/repositories/sqlite.py
```

Expected: empty.

- [ ] **Step 3: Update `tests/unit/test_sqlite_repository.py`**

Delete every test that exercises category methods. Remove category rows from shared SQL fixtures. Verify:

```bash
grep -n -i categor tests/unit/test_sqlite_repository.py
```

Expected: empty.

- [ ] **Step 4: Run the repository tests**

```bash
pytest tests/unit/test_sqlite_repository.py -v
```

Expected: all pass. (The schema still contains the `categories` table and `category_id` column at this point — that's fine; tests just never touch them.)

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/repositories/sqlite.py tests/unit/test_sqlite_repository.py
git commit -m "refactor(repo): remove category methods and SQL from MetadataRepository"
```

---

## Task 7: Remove Category from Domain Models

**Files:**
- Modify: `src/image_vector_search/domain/models.py`
- Modify: `tests/unit/test_domain_models.py`

- [ ] **Step 1: Delete `Category` and `CategoryNode` classes**

In `domain/models.py`, delete the whole `class Category(BaseModel): ...` (currently lines 22–27) and the whole `class CategoryNode(BaseModel): ...` (currently lines 30–39).

- [ ] **Step 2: Remove `categories` field from image result types**

In `SearchResult` (currently line 72), delete:

```python
categories: list[Category] = []
```

In `ImageRecordWithLabels` (currently line 106), delete:

```python
categories: list[Category] = []
```

- [ ] **Step 3: Verify no remaining references**

```bash
grep -n -i category src/image_vector_search/domain/models.py
```

Expected: empty.

- [ ] **Step 4: Update `tests/unit/test_domain_models.py`**

Strip category assertions. Verify:

```bash
grep -n -i categor tests/unit/test_domain_models.py
```

Expected: empty.

- [ ] **Step 5: Run domain tests**

```bash
pytest tests/unit/test_domain_models.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/image_vector_search/domain/models.py tests/unit/test_domain_models.py
git commit -m "refactor(domain): remove Category and CategoryNode models"
```

---

## Task 8: Update Schema and Add Startup Drop Migration

**Files:**
- Modify: `src/image_vector_search/repositories/schema.sql`
- Modify: `src/image_vector_search/repositories/sqlite.py` (add `_drop_category_schema` migration method)
- Create: `tests/unit/test_drop_category_migration.py`

- [ ] **Step 1: Rewrite `schema.sql`**

Replace the current category-aware `image_tags` definition (currently lines 69–82) and the entire `categories` block (currently lines 56–67) with:

```sql
CREATE TABLE IF NOT EXISTS image_tags (
    content_hash  TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    tag_id        INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (content_hash, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_image_tags_content_hash ON image_tags(content_hash);
CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
```

Delete lines referencing `categories` (the `CREATE TABLE categories`, the `idx_categories_root_name` unique index, and `idx_image_tags_category_id`). Verify:

```bash
grep -n -i categor src/image_vector_search/repositories/schema.sql
```

Expected: empty.

- [ ] **Step 2: Write the migration unit test first**

Create `tests/unit/test_drop_category_migration.py`:

```python
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from image_vector_search.repositories.sqlite import MetadataRepository


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_legacy_db(path: Path) -> None:
    """Create a DB that matches the schema *before* the category removal."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE images (
          content_hash TEXT PRIMARY KEY,
          canonical_path TEXT NOT NULL,
          file_size INTEGER NOT NULL,
          mtime REAL NOT NULL,
          mime_type TEXT NOT NULL,
          width INTEGER NOT NULL,
          height INTEGER NOT NULL,
          is_active INTEGER NOT NULL,
          last_seen_at TEXT NOT NULL,
          embedding_provider TEXT NOT NULL,
          embedding_model TEXT NOT NULL,
          embedding_version TEXT NOT NULL,
          embedding_status TEXT NOT NULL DEFAULT 'embedded',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL
        );
        CREATE TABLE categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          parent_id INTEGER REFERENCES categories(id),
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          UNIQUE(parent_id, name)
        );
        CREATE TABLE image_tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          content_hash TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
          category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
          created_at TEXT NOT NULL,
          UNIQUE(content_hash, tag_id),
          UNIQUE(content_hash, category_id),
          CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))
        );
        CREATE INDEX idx_image_tags_category_id ON image_tags(category_id);
        """
    )
    now = _iso_now()
    conn.execute(
        "INSERT INTO images VALUES ('h1','/img/1.jpg',1,0,'image/jpeg',1,1,1,?, 'jina','v1','1','embedded',?,?)",
        (now, now, now),
    )
    conn.execute("INSERT INTO tags (name, created_at) VALUES ('red', ?)", (now,))
    conn.execute("INSERT INTO categories (name, parent_id, created_at) VALUES ('Nature', NULL, ?)", (now,))
    conn.execute(
        "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES ('h1', 1, NULL, ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES ('h1', NULL, 1, ?)",
        (now,),
    )
    conn.commit()
    conn.close()


def test_drop_category_schema_migrates_legacy_db(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite"
    _build_legacy_db(db_path)

    MetadataRepository(db_path)  # triggers migrations on init

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "categories" not in tables

        columns = {row[1] for row in conn.execute("PRAGMA table_info(image_tags)")}
        assert "category_id" not in columns
        assert columns >= {"content_hash", "tag_id", "created_at"}

        rows = conn.execute("SELECT content_hash, tag_id FROM image_tags").fetchall()
        assert rows == [("h1", 1)]  # tag row survived; category row dropped
    finally:
        conn.close()


def test_drop_category_schema_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.sqlite"
    MetadataRepository(db_path)  # fresh install
    MetadataRepository(db_path)  # second init must not error

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "categories" not in tables
    finally:
        conn.close()
```

- [ ] **Step 3: Run the test and verify it fails**

```bash
pytest tests/unit/test_drop_category_migration.py -v
```

Expected: both tests FAIL. The first because `categories` table still exists after migration; the second because `MetadataRepository` may also fail on fresh init if the schema file hasn't been updated yet (Step 1 of this task did update it — so only the first test should fail initially, because there is no migration function yet).

- [ ] **Step 4: Add the migration method to `MetadataRepository`**

In `sqlite.py`, alongside `_ensure_embedding_status_column` and `_ensure_album_schema`, add:

```python
def _drop_category_schema(self, connection: sqlite3.Connection) -> None:
    tables = {
        str(row["name"])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "categories" not in tables:
        return

    connection.execute(
        """
        CREATE TABLE image_tags__new (
            content_hash  TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
            tag_id        INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            created_at    TEXT NOT NULL,
            PRIMARY KEY (content_hash, tag_id)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO image_tags__new (content_hash, tag_id, created_at)
            SELECT content_hash, tag_id, created_at
              FROM image_tags
             WHERE tag_id IS NOT NULL
        """
    )
    connection.execute("DROP TABLE image_tags")
    connection.execute("ALTER TABLE image_tags__new RENAME TO image_tags")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_image_tags_content_hash ON image_tags(content_hash)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id)"
    )
    connection.execute("DROP TABLE categories")
    connection.execute("DROP INDEX IF EXISTS idx_image_tags_category_id")
    connection.execute("DROP INDEX IF EXISTS idx_categories_root_name")
```

- [ ] **Step 5: Call the migration at startup**

Find the init method that currently calls `_ensure_embedding_status_column(...)` and `_ensure_album_schema(...)` (the existing idempotent migration block in `MetadataRepository.__init__` / `_initialize`). Add a call to `self._drop_category_schema(connection)` immediately after those — inside the same transaction. If the existing pattern uses a `with connection:` block, reuse it; otherwise follow the surrounding conventions exactly.

- [ ] **Step 6: Run the migration test**

```bash
pytest tests/unit/test_drop_category_migration.py -v
```

Expected: both tests PASS.

- [ ] **Step 7: Run the full backend test suite**

```bash
pytest -x
```

Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/image_vector_search/repositories/schema.sql \
        src/image_vector_search/repositories/sqlite.py \
        tests/unit/test_drop_category_migration.py
git commit -m "feat(schema): drop categories table and rebuild image_tags at startup"
```

---

## Task 9: Cross-Cutting Test Sweep

**Files:** whatever still references categories in `tests/` or `src/`.

- [ ] **Step 1: Run the residual grep**

```bash
grep -rni "categor" src/ tests/
```

- [ ] **Step 2: Fix each hit**

For every file the grep returns (except historical design docs under `docs/plans/`, which are left untouched):

- If it's a test, delete the relevant test or strip the assertion.
- If it's production code, delete the reference.

Re-run the grep until it returns nothing under `src/` and `tests/`.

- [ ] **Step 3: Run the full backend test suite**

```bash
pytest
```

Expected: all pass.

- [ ] **Step 4: Run the frontend suite**

```bash
cd src/image_vector_search/frontend && npm run test -- --run && npx tsc --noEmit
```

Expected: both pass.

- [ ] **Step 5: Commit (if anything changed)**

```bash
git add -A
git commit -m "test: strip residual category references"
```

If nothing changed, skip the commit.

---

## Task 10: Documentation Sweep

**Files:**
- Modify: `docs/usage.md`
- Modify: `docs/api.md`

- [ ] **Step 1: `docs/usage.md`**

Remove the section that describes Category as an organization concept. If the doc has a "Organizing images" intro that lists Folders/Tags/Categories/Albums, update it to list only Folders/Tags/Albums.

```bash
grep -n -i categor docs/usage.md
```

Expected after edits: empty.

- [ ] **Step 2: `docs/api.md`**

Remove every Category endpoint from the reference. Verify:

```bash
grep -n -i categor docs/api.md
```

Expected: empty.

- [ ] **Step 3: Final sweep across tracked, non-historical surfaces**

```bash
grep -rni "categor" src/ tests/ docs/usage.md docs/api.md
```

Expected: empty. (Historical design docs in `docs/plans/` and `docs/superpowers/specs/` are intentionally left alone — they describe past decisions.)

- [ ] **Step 4: Full suite once more**

```bash
pytest
cd src/image_vector_search/frontend && npm run test -- --run && npx tsc --noEmit
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add docs/usage.md docs/api.md
git commit -m "docs: drop Category from usage and API reference"
```

---

## Done Criteria

- `grep -rni "categor" src/ tests/ docs/usage.md docs/api.md` returns no matches.
- `pytest` passes.
- `npm run test -- --run` and `npx tsc --noEmit` (frontend) pass.
- Starting the server against a legacy DB (one containing a `categories` table) runs the drop migration once, preserves tag-only `image_tags` rows, and removes the `categories` table and `idx_image_tags_category_id` index.
- Fresh-install DB boots with the new schema and no `categories` table.
- `manage_categories` is no longer in the MCP tool catalogue, and the image-tagging tool no longer advertises `add_category`/`remove_category`/`list_categories`.
