# Purge Inactive Images Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an admin workflow to review and purge selected inactive image records from metadata and vector index storage without touching source image files.

**Architecture:** Extend the status stack with inactive-image listing and purge operations, expose them through dedicated web routes, and wire a dashboard dialog that loads inactive records, defaults all checkboxes to selected, and submits the chosen hashes for deletion. Purge only applies to inactive records and removes both SQLite metadata and current-embedding vector rows.

**Tech Stack:** FastAPI, SQLite, Milvus Lite, React, TanStack Query, Vitest, pytest

---

### Task 1: Repository purge support

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Test: `tests/unit/test_sqlite_repository.py`

**Step 1: Write the failing test**

```python
def test_purge_images_deletes_inactive_records_and_relations(tmp_path):
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_sqlite_repository.py -k purge_images -v`
Expected: FAIL because purge/list methods do not exist yet.

**Step 3: Write minimal implementation**

Add repository methods to list inactive images and delete image rows for selected hashes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_sqlite_repository.py -k purge_images -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_sqlite_repository.py src/image_vector_search/repositories/sqlite.py
git commit -m "feat: add inactive image purge repository support"
```

### Task 2: Status service and API endpoints

**Files:**
- Modify: `src/image_vector_search/services/status.py`
- Modify: `src/image_vector_search/adapters/vector_index/base.py`
- Modify: `src/image_vector_search/adapters/vector_index/milvus_lite.py`
- Modify: `src/image_vector_search/frontend/routes.py`
- Test: `tests/integration/test_web_admin.py`

**Step 1: Write the failing test**

```python
def test_inactive_images_api_lists_records():
    ...

def test_purge_inactive_images_api_removes_selected_records():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_web_admin.py -k inactive -v`
Expected: FAIL because API routes and service methods do not exist.

**Step 3: Write minimal implementation**

Add status-service orchestration, vector-index deletion, and new inactive image routes.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_web_admin.py -k inactive -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/test_web_admin.py src/image_vector_search/services/status.py src/image_vector_search/adapters/vector_index/base.py src/image_vector_search/adapters/vector_index/milvus_lite.py src/image_vector_search/frontend/routes.py
git commit -m "feat: expose inactive image purge api"
```

### Task 3: Dashboard selection dialog

**Files:**
- Modify: `src/image_vector_search/frontend/src/api/images.ts`
- Modify: `src/image_vector_search/frontend/src/api/types.ts`
- Modify: `src/image_vector_search/frontend/src/pages/DashboardPage.tsx`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Write the failing test**

```tsx
it("defaults inactive purge dialog to all selected and submits chosen hashes", async () => {
  ...
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- admin-navigation.test.tsx`
Expected: FAIL because the purge dialog and mutations do not exist.

**Step 3: Write minimal implementation**

Add inactive-image query/mutation hooks and a dashboard dialog with default-all selection.

**Step 4: Run test to verify it passes**

Run: `npm test -- admin-navigation.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/api/images.ts src/image_vector_search/frontend/src/api/types.ts src/image_vector_search/frontend/src/pages/DashboardPage.tsx src/image_vector_search/frontend/src/test/admin-navigation.test.tsx
git commit -m "feat: add dashboard inactive purge workflow"
```

### Task 4: Full verification

**Files:**
- Modify: none expected
- Test: `tests/unit/test_sqlite_repository.py`
- Test: `tests/integration/test_web_admin.py`
- Test: `src/image_vector_search/frontend/src/test/admin-navigation.test.tsx`

**Step 1: Run backend verification**

Run: `pytest tests/unit/test_sqlite_repository.py tests/integration/test_web_admin.py -v`
Expected: PASS

**Step 2: Run frontend verification**

Run: `npm test -- admin-navigation.test.tsx`
Expected: PASS

**Step 3: Fix any regressions**

Apply minimal follow-up edits only if a verification step fails.

**Step 4: Re-run verification**

Repeat the failing command until all targeted tests pass.

**Step 5: Commit**

```bash
git add -A
git commit -m "test: verify inactive purge workflow"
```
