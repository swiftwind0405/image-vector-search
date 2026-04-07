# Bulk Operations & File Open Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bulk tag/category operations (by selection and by folder), folder filtering, and file open/reveal to the admin console Images page.

**Architecture:** Backend adds repository bulk methods, TagService bulk methods, and new HTTP routes for bulk ops, folder listing, and file operations. Frontend adds folder filter dropdown, checkbox selection with floating bulk action bar, folder quick actions dialog, and open/reveal file buttons. All bulk database operations are atomic single-transaction operations.

**Tech Stack:** Python (FastAPI, SQLite, subprocess), React 18 + TypeScript (TanStack React Query, shadcn/ui)

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `src/image_vector_search/repositories/sqlite.py` | Add `list_folders()`, extend `list_active_images()` with folder filter, add 4 bulk methods + 4 folder-bulk methods |
| Modify | `src/image_vector_search/services/tagging.py` | Add 8 bulk service methods with validation |
| Modify | `src/image_vector_search/services/status.py` | Extend `list_active_images()` with folder param |
| Create | `src/image_vector_search/frontend/bulk_routes.py` | HTTP routes for bulk ops, folders, file open/reveal |
| Modify | `src/image_vector_search/frontend/routes.py` | Extend `GET /api/images` with `folder` query param |
| Modify | `src/image_vector_search/app.py` | Register bulk router |
| Create | `src/image_vector_search/frontend/src/api/bulk.ts` | React Query hooks for all bulk + folder + file operations |
| Modify | `src/image_vector_search/frontend/src/api/images.ts` | Add `folder` param to `useImages()` |
| Modify | `src/image_vector_search/frontend/src/api/types.ts` | Add `BulkResponse` type |
| Modify | `src/image_vector_search/frontend/src/pages/ImagesPage.tsx` | Folder filter, checkboxes, bulk action bar, file buttons, folder actions dialog |
| Create | `tests/unit/test_bulk_service.py` | Unit tests for TagService bulk methods |
| Create | `tests/integration/test_bulk_api.py` | Integration tests for all bulk + folder + file endpoints |

---

### Task 1: Repository Bulk Methods

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Create: `tests/unit/test_bulk_repository.py`

This task adds all new repository methods: `list_folders`, folder-filtered `list_active_images`, and 4 bulk add/remove methods for tags and categories.

- [ ] **Step 1: Write tests for `list_folders`**

```python
# tests/unit/test_bulk_repository.py
import pytest
from datetime import datetime, timezone
from pathlib import Path
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.domain.models import ImageRecord

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_image(content_hash: str, canonical_path: str) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=True,
        last_seen_at=NOW,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=NOW,
        updated_at=NOW,
    )


class TestListFolders:
    @pytest.fixture
    def repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        return repo

    def test_empty_returns_empty(self, repo):
        assert repo.list_folders("/data/images") == []

    def test_returns_distinct_parent_dirs_relative(self, repo):
        repo.upsert_image(_make_image("aaa", "/data/images/nature/flowers/rose.jpg"))
        repo.upsert_image(_make_image("bbb", "/data/images/nature/flowers/tulip.jpg"))
        repo.upsert_image(_make_image("ccc", "/data/images/urban/city.jpg"))
        folders = repo.list_folders("/data/images")
        assert folders == ["nature/flowers", "urban"]

    def test_inactive_images_excluded(self, repo):
        img = _make_image("aaa", "/data/images/nature/rose.jpg")
        img.is_active = False
        repo.upsert_image(img)
        assert repo.list_folders("/data/images") == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bulk_repository.py -v`
Expected: FAIL — `list_folders` method does not exist

- [ ] **Step 3: Implement `list_folders`**

Add to `MetadataRepository` in `src/image_vector_search/repositories/sqlite.py`, after the existing `list_active_images` method:

```python
def list_folders(self, images_root: str) -> list[str]:
    """Return distinct parent directories of active images, relative to images_root, sorted."""
    with self.connect() as connection:
        rows = connection.execute(
            "SELECT DISTINCT canonical_path FROM images WHERE is_active = 1"
        ).fetchall()
    prefix = images_root.rstrip("/") + "/"
    folders: set[str] = set()
    for row in rows:
        path = str(row["canonical_path"])
        if path.startswith(prefix):
            relative = path[len(prefix):]
            parent = "/".join(relative.split("/")[:-1])
            if parent:
                folders.add(parent)
    return sorted(folders)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bulk_repository.py::TestListFolders -v`
Expected: PASS

- [ ] **Step 5: Write tests for folder-filtered `list_active_images`**

Append to `tests/unit/test_bulk_repository.py`:

```python
class TestListActiveImagesWithFolder:
    @pytest.fixture
    def repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        repo.upsert_image(_make_image("aaa", "/data/images/nature/flowers/rose.jpg"))
        repo.upsert_image(_make_image("bbb", "/data/images/urban/city.jpg"))
        return repo

    def test_no_folder_returns_all(self, repo):
        images = repo.list_active_images()
        assert len(images) == 2

    def test_folder_filters_by_prefix(self, repo):
        images = repo.list_active_images(folder="nature", images_root="/data/images")
        assert len(images) == 1
        assert images[0].content_hash == "aaa"

    def test_nonexistent_folder_returns_empty(self, repo):
        images = repo.list_active_images(folder="missing", images_root="/data/images")
        assert len(images) == 0
```

- [ ] **Step 6: Run tests to verify they fail**

Run: `pytest tests/unit/test_bulk_repository.py::TestListActiveImagesWithFolder -v`
Expected: FAIL — `list_active_images` does not accept `folder`/`images_root` params

- [ ] **Step 7: Extend `list_active_images` with folder filtering**

Replace the existing `list_active_images` method in `src/image_vector_search/repositories/sqlite.py`:

```python
def list_active_images(self, folder: str | None = None, images_root: str | None = None) -> list[ImageRecord]:
    with self.connect() as connection:
        if folder and images_root:
            prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
            rows = connection.execute(
                "SELECT * FROM images WHERE is_active = 1 AND canonical_path LIKE ? ORDER BY canonical_path ASC",
                (prefix + "%",),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM images WHERE is_active = 1 ORDER BY canonical_path ASC"
            ).fetchall()
    return [_row_to_image(row) for row in rows]
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/unit/test_bulk_repository.py -v`
Expected: PASS

- [ ] **Step 9: Write tests for bulk add/remove tag**

Append to `tests/unit/test_bulk_repository.py`:

```python
class TestBulkTagOperations:
    @pytest.fixture
    def repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        repo.upsert_image(_make_image("aaa", "/data/images/a.jpg"))
        repo.upsert_image(_make_image("bbb", "/data/images/b.jpg"))
        return repo

    def test_bulk_add_tag(self, repo):
        tag = repo.create_tag("sunset")
        affected = repo.bulk_add_tag(["aaa", "bbb"], tag.id)
        assert affected == 2
        assert len(repo.get_image_tags("aaa")) == 1
        assert len(repo.get_image_tags("bbb")) == 1

    def test_bulk_add_tag_idempotent(self, repo):
        tag = repo.create_tag("sunset")
        repo.bulk_add_tag(["aaa"], tag.id)
        affected = repo.bulk_add_tag(["aaa", "bbb"], tag.id)
        assert affected == 1  # only bbb is new

    def test_bulk_remove_tag(self, repo):
        tag = repo.create_tag("sunset")
        repo.bulk_add_tag(["aaa", "bbb"], tag.id)
        affected = repo.bulk_remove_tag(["aaa"], tag.id)
        assert affected == 1
        assert len(repo.get_image_tags("aaa")) == 0
        assert len(repo.get_image_tags("bbb")) == 1

    def test_bulk_remove_tag_nonexistent_is_zero(self, repo):
        tag = repo.create_tag("sunset")
        affected = repo.bulk_remove_tag(["aaa"], tag.id)
        assert affected == 0

    def test_bulk_add_category(self, repo):
        cat = repo.create_category("Nature")
        affected = repo.bulk_add_category(["aaa", "bbb"], cat.id)
        assert affected == 2

    def test_bulk_remove_category(self, repo):
        cat = repo.create_category("Nature")
        repo.bulk_add_category(["aaa", "bbb"], cat.id)
        affected = repo.bulk_remove_category(["aaa"], cat.id)
        assert affected == 1
```

- [ ] **Step 10: Run tests to verify they fail**

Run: `pytest tests/unit/test_bulk_repository.py::TestBulkTagOperations -v`
Expected: FAIL — `bulk_add_tag` does not exist

- [ ] **Step 11: Implement bulk add/remove methods**

Add to `MetadataRepository` in `src/image_vector_search/repositories/sqlite.py`:

```python
def bulk_add_tag(self, content_hashes: list[str], tag_id: int) -> int:
    if not content_hashes:
        return 0
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        cursor = conn.executemany(
            "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
            [(h, tag_id, now) for h in content_hashes],
        )
        return cursor.rowcount

def bulk_remove_tag(self, content_hashes: list[str], tag_id: int) -> int:
    if not content_hashes:
        return 0
    with self.connect() as conn:
        placeholders = ",".join("?" * len(content_hashes))
        cursor = conn.execute(
            f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND tag_id = ?",
            [*content_hashes, tag_id],
        )
        return cursor.rowcount

def bulk_add_category(self, content_hashes: list[str], category_id: int) -> int:
    if not content_hashes:
        return 0
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        cursor = conn.executemany(
            "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
            [(h, category_id, now) for h in content_hashes],
        )
        return cursor.rowcount

def bulk_remove_category(self, content_hashes: list[str], category_id: int) -> int:
    if not content_hashes:
        return 0
    with self.connect() as conn:
        placeholders = ",".join("?" * len(content_hashes))
        cursor = conn.execute(
            f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND category_id = ?",
            [*content_hashes, category_id],
        )
        return cursor.rowcount
```

- [ ] **Step 12: Run all repository tests**

Run: `pytest tests/unit/test_bulk_repository.py -v`
Expected: ALL PASS

- [ ] **Step 13: Run full test suite to check for regressions**

Run: `pytest -v`
Expected: No regressions from `list_active_images` signature change (existing callers pass no args)

- [ ] **Step 14: Commit**

```bash
git add src/image_vector_search/repositories/sqlite.py tests/unit/test_bulk_repository.py
git commit -m "feat: add repository bulk methods and folder listing"
```

---

### Task 2: Repository Folder-Bulk Methods

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Modify: `tests/unit/test_bulk_repository.py`

These are dedicated methods that resolve folder → content_hashes → bulk operation in a single transaction.

- [ ] **Step 1: Write tests for folder-bulk operations**

Append to `tests/unit/test_bulk_repository.py`:

```python
class TestFolderBulkOperations:
    @pytest.fixture
    def repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        repo.upsert_image(_make_image("aaa", "/data/images/nature/rose.jpg"))
        repo.upsert_image(_make_image("bbb", "/data/images/nature/tulip.jpg"))
        repo.upsert_image(_make_image("ccc", "/data/images/urban/city.jpg"))
        return repo

    def test_bulk_folder_add_tag(self, repo):
        tag = repo.create_tag("flowers")
        affected = repo.bulk_folder_add_tag("nature", tag.id, "/data/images")
        assert affected == 2
        assert len(repo.get_image_tags("aaa")) == 1
        assert len(repo.get_image_tags("ccc")) == 0

    def test_bulk_folder_remove_tag(self, repo):
        tag = repo.create_tag("flowers")
        repo.bulk_folder_add_tag("nature", tag.id, "/data/images")
        affected = repo.bulk_folder_remove_tag("nature", tag.id, "/data/images")
        assert affected == 2
        assert len(repo.get_image_tags("aaa")) == 0

    def test_bulk_folder_add_category(self, repo):
        cat = repo.create_category("Nature")
        affected = repo.bulk_folder_add_category("nature", cat.id, "/data/images")
        assert affected == 2

    def test_bulk_folder_remove_category(self, repo):
        cat = repo.create_category("Nature")
        repo.bulk_folder_add_category("nature", cat.id, "/data/images")
        affected = repo.bulk_folder_remove_category("nature", cat.id, "/data/images")
        assert affected == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bulk_repository.py::TestFolderBulkOperations -v`
Expected: FAIL

- [ ] **Step 3: Implement folder-bulk methods**

Add to `MetadataRepository` in `src/image_vector_search/repositories/sqlite.py`:

```python
def bulk_folder_add_tag(self, folder: str, tag_id: int, images_root: str) -> int:
    prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        rows = conn.execute(
            "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
            (prefix + "%",),
        ).fetchall()
        hashes = [r["content_hash"] for r in rows]
        if not hashes:
            return 0
        cursor = conn.executemany(
            "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
            [(h, tag_id, now) for h in hashes],
        )
        return cursor.rowcount

def bulk_folder_remove_tag(self, folder: str, tag_id: int, images_root: str) -> int:
    prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
    with self.connect() as conn:
        rows = conn.execute(
            "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
            (prefix + "%",),
        ).fetchall()
        hashes = [r["content_hash"] for r in rows]
        if not hashes:
            return 0
        placeholders = ",".join("?" * len(hashes))
        cursor = conn.execute(
            f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND tag_id = ?",
            [*hashes, tag_id],
        )
        return cursor.rowcount

def bulk_folder_add_category(self, folder: str, category_id: int, images_root: str) -> int:
    prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        rows = conn.execute(
            "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
            (prefix + "%",),
        ).fetchall()
        hashes = [r["content_hash"] for r in rows]
        if not hashes:
            return 0
        cursor = conn.executemany(
            "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
            [(h, category_id, now) for h in hashes],
        )
        return cursor.rowcount

def bulk_folder_remove_category(self, folder: str, category_id: int, images_root: str) -> int:
    prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
    with self.connect() as conn:
        rows = conn.execute(
            "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
            (prefix + "%",),
        ).fetchall()
        hashes = [r["content_hash"] for r in rows]
        if not hashes:
            return 0
        placeholders = ",".join("?" * len(hashes))
        cursor = conn.execute(
            f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND category_id = ?",
            [*hashes, category_id],
        )
        return cursor.rowcount
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bulk_repository.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/repositories/sqlite.py tests/unit/test_bulk_repository.py
git commit -m "feat: add folder-bulk repository methods with single-transaction atomicity"
```

---

### Task 3: TagService Bulk Methods

**Files:**
- Modify: `src/image_vector_search/services/tagging.py`
- Create: `tests/unit/test_bulk_service.py`

Add bulk methods to TagService with validation (max 500 hashes, catch IntegrityError).

- [ ] **Step 1: Write tests for bulk service validation and delegation**

```python
# tests/unit/test_bulk_service.py
import sqlite3
import pytest
from unittest.mock import MagicMock
from image_vector_search.services.tagging import TagService


class TestBulkTagServiceValidation:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    def test_bulk_add_tag_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_add_tag.return_value = 3
        result = svc.bulk_add_tag(["a", "b", "c"], 1)
        repo.bulk_add_tag.assert_called_once_with(["a", "b", "c"], 1)
        assert result == 3

    def test_bulk_add_tag_exceeds_max_raises(self):
        svc, repo = self._make_service()
        hashes = [f"h{i}" for i in range(501)]
        with pytest.raises(ValueError, match="500"):
            svc.bulk_add_tag(hashes, 1)

    def test_bulk_add_tag_invalid_tag_id_raises(self):
        svc, repo = self._make_service()
        repo.bulk_add_tag.side_effect = sqlite3.IntegrityError("FOREIGN KEY constraint failed")
        with pytest.raises(ValueError, match="tag_id"):
            svc.bulk_add_tag(["aaa"], 999)

    def test_bulk_remove_tag_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_remove_tag.return_value = 2
        result = svc.bulk_remove_tag(["a", "b"], 1)
        assert result == 2

    def test_bulk_add_category_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_add_category.return_value = 2
        result = svc.bulk_add_category(["a", "b"], 1)
        assert result == 2

    def test_bulk_add_category_invalid_id_raises(self):
        svc, repo = self._make_service()
        repo.bulk_add_category.side_effect = sqlite3.IntegrityError("FOREIGN KEY constraint failed")
        with pytest.raises(ValueError, match="category_id"):
            svc.bulk_add_category(["aaa"], 999)

    def test_bulk_remove_category_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_remove_category.return_value = 1
        result = svc.bulk_remove_category(["a"], 1)
        assert result == 1

    def test_bulk_folder_add_tag_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_tag.return_value = 5
        result = svc.bulk_folder_add_tag("nature", 1, "/data/images")
        repo.bulk_folder_add_tag.assert_called_once_with("nature", 1, "/data/images")
        assert result == 5

    def test_bulk_folder_remove_tag_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_folder_remove_tag.return_value = 3
        result = svc.bulk_folder_remove_tag("nature", 1, "/data/images")
        assert result == 3

    def test_bulk_folder_add_category_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_category.return_value = 4
        result = svc.bulk_folder_add_category("nature", 1, "/data/images")
        assert result == 4

    def test_bulk_folder_remove_category_delegates(self):
        svc, repo = self._make_service()
        repo.bulk_folder_remove_category.return_value = 2
        result = svc.bulk_folder_remove_category("nature", 1, "/data/images")
        assert result == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_bulk_service.py -v`
Expected: FAIL — `bulk_add_tag` not on TagService

- [ ] **Step 3: Implement TagService bulk methods**

Add to `TagService` class in `src/image_vector_search/services/tagging.py`. First add `import sqlite3` at the top of the file. Then add these as class members after the image associations section (indented inside the class body):

```python
    # --- Bulk operations ---

    MAX_BULK_SIZE = 500

    def bulk_add_tag(self, content_hashes: list[str], tag_id: int) -> int:
    if len(content_hashes) > self.MAX_BULK_SIZE:
        raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
    try:
        return self._repo.bulk_add_tag(content_hashes, tag_id)
    except sqlite3.IntegrityError:
        raise ValueError(f"Invalid tag_id: {tag_id}")

def bulk_remove_tag(self, content_hashes: list[str], tag_id: int) -> int:
    if len(content_hashes) > self.MAX_BULK_SIZE:
        raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
    return self._repo.bulk_remove_tag(content_hashes, tag_id)

def bulk_add_category(self, content_hashes: list[str], category_id: int) -> int:
    if len(content_hashes) > self.MAX_BULK_SIZE:
        raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
    try:
        return self._repo.bulk_add_category(content_hashes, category_id)
    except sqlite3.IntegrityError:
        raise ValueError(f"Invalid category_id: {category_id}")

def bulk_remove_category(self, content_hashes: list[str], category_id: int) -> int:
    if len(content_hashes) > self.MAX_BULK_SIZE:
        raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
    return self._repo.bulk_remove_category(content_hashes, category_id)

def bulk_folder_add_tag(self, folder: str, tag_id: int, images_root: str) -> int:
    try:
        return self._repo.bulk_folder_add_tag(folder, tag_id, images_root)
    except sqlite3.IntegrityError:
        raise ValueError(f"Invalid tag_id: {tag_id}")

def bulk_folder_remove_tag(self, folder: str, tag_id: int, images_root: str) -> int:
    return self._repo.bulk_folder_remove_tag(folder, tag_id, images_root)

def bulk_folder_add_category(self, folder: str, category_id: int, images_root: str) -> int:
    try:
        return self._repo.bulk_folder_add_category(folder, category_id, images_root)
    except sqlite3.IntegrityError:
        raise ValueError(f"Invalid category_id: {category_id}")

def bulk_folder_remove_category(self, folder: str, category_id: int, images_root: str) -> int:
    return self._repo.bulk_folder_remove_category(folder, category_id, images_root)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_bulk_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/services/tagging.py tests/unit/test_bulk_service.py
git commit -m "feat: add TagService bulk methods with validation"
```

---

### Task 4: StatusService Folder Filtering & Routes Update

**Files:**
- Modify: `src/image_vector_search/services/status.py`
- Modify: `src/image_vector_search/frontend/routes.py`

Extend `list_active_images()` on StatusService and the `GET /api/images` endpoint to accept a folder filter.

- [ ] **Step 1: Extend StatusService**

In `src/image_vector_search/services/status.py`, change `list_active_images`:

```python
def list_active_images(self, folder: str | None = None) -> list[ImageRecord]:
    images_root = str(self.settings.images_root) if folder else None
    return self.repository.list_active_images(folder=folder, images_root=images_root)
```

- [ ] **Step 2: Extend `GET /api/images` in routes.py**

In `src/image_vector_search/frontend/routes.py`, change the `list_images` endpoint:

```python
@router.get("/api/images")
async def list_images(folder: str | None = None):
    return JSONResponse(
        content=jsonable_encoder(status_service.list_active_images(folder=folder))
    )
```

- [ ] **Step 3: Run full test suite**

Run: `pytest -v`
Expected: ALL PASS (no regressions — existing callers still work with default `None`)

- [ ] **Step 4: Commit**

```bash
git add src/image_vector_search/services/status.py src/image_vector_search/frontend/routes.py
git commit -m "feat: extend GET /api/images with folder query param"
```

---

### Task 5: Bulk & File Operations HTTP Routes

**Files:**
- Create: `src/image_vector_search/frontend/bulk_routes.py`
- Modify: `src/image_vector_search/app.py`
- Create: `tests/integration/test_bulk_api.py`

Create all HTTP endpoints for bulk operations, folder listing, and file open/reveal.

- [ ] **Step 1: Write integration tests for bulk endpoints**

```python
# tests/integration/test_bulk_api.py
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.tagging import TagService
from image_vector_search.api.tag_routes import create_tag_router
from image_vector_search.api.bulk_routes import create_bulk_router
from image_vector_search.domain.models import ImageRecord
from datetime import datetime, timezone

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_image(content_hash: str, canonical_path: str) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=True,
        last_seen_at=NOW,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def app(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    # Seed images
    repo.upsert_image(_make_image("aaa", "/data/images/nature/rose.jpg"))
    repo.upsert_image(_make_image("bbb", "/data/images/nature/tulip.jpg"))
    repo.upsert_image(_make_image("ccc", "/data/images/urban/city.jpg"))
    tag_service = TagService(repository=repo)
    app = FastAPI()
    app.include_router(create_tag_router(tag_service=tag_service))
    app.include_router(create_bulk_router(tag_service=tag_service, images_root="/data/images"))
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFolderEndpoints:
    @pytest.mark.anyio
    async def test_list_folders(self, client):
        resp = await client.get("/api/folders")
        assert resp.status_code == 200
        folders = resp.json()
        assert "nature" in folders
        assert "urban" in folders


class TestBulkBySelection:
    @pytest.mark.anyio
    async def test_bulk_add_tag(self, client):
        tag_resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = tag_resp.json()["id"]
        resp = await client.post("/api/bulk/tags/add", json={
            "content_hashes": ["aaa", "bbb"],
            "tag_id": tag_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_remove_tag(self, client):
        tag_resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = tag_resp.json()["id"]
        await client.post("/api/bulk/tags/add", json={
            "content_hashes": ["aaa", "bbb"],
            "tag_id": tag_id,
        })
        resp = await client.post("/api/bulk/tags/remove", json={
            "content_hashes": ["aaa"],
            "tag_id": tag_id,
        })
        assert resp.status_code == 200
        assert resp.json()["affected"] == 1

    @pytest.mark.anyio
    async def test_bulk_add_category(self, client):
        cat_resp = await client.post("/api/categories", json={"name": "Nature"})
        cat_id = cat_resp.json()["id"]
        resp = await client.post("/api/bulk/categories/add", json={
            "content_hashes": ["aaa", "bbb"],
            "category_id": cat_id,
        })
        assert resp.status_code == 200
        assert resp.json()["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_exceeds_max_returns_400(self, client):
        tag_resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = tag_resp.json()["id"]
        hashes = [f"h{i}" for i in range(501)]
        resp = await client.post("/api/bulk/tags/add", json={
            "content_hashes": hashes,
            "tag_id": tag_id,
        })
        assert resp.status_code == 400


class TestBulkByFolder:
    @pytest.mark.anyio
    async def test_bulk_folder_add_tag(self, client):
        tag_resp = await client.post("/api/tags", json={"name": "flowers"})
        tag_id = tag_resp.json()["id"]
        resp = await client.post("/api/bulk/folder/tags/add", json={
            "folder": "nature",
            "tag_id": tag_id,
        })
        assert resp.status_code == 200
        assert resp.json()["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_folder_remove_tag(self, client):
        tag_resp = await client.post("/api/tags", json={"name": "flowers"})
        tag_id = tag_resp.json()["id"]
        await client.post("/api/bulk/folder/tags/add", json={
            "folder": "nature",
            "tag_id": tag_id,
        })
        resp = await client.post("/api/bulk/folder/tags/remove", json={
            "folder": "nature",
            "tag_id": tag_id,
        })
        assert resp.status_code == 200
        assert resp.json()["affected"] == 2


class TestFileOperations:
    @pytest.mark.anyio
    async def test_open_file_not_found(self, client):
        resp = await client.post("/api/files/open", json={"path": "/data/images/nope.jpg"})
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_open_file_outside_root(self, client):
        resp = await client.post("/api/files/open", json={"path": "/etc/passwd"})
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_reveal_file_outside_root(self, client):
        resp = await client.post("/api/files/reveal", json={"path": "/etc/passwd"})
        assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_bulk_api.py -v`
Expected: FAIL — `bulk_routes` module does not exist

- [ ] **Step 3: Implement `bulk_routes.py`**

Create `src/image_vector_search/frontend/bulk_routes.py`:

```python
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from image_vector_search.services.tagging import TagService


class BulkTagRequest(BaseModel):
    content_hashes: list[str] = Field(..., max_length=500)
    tag_id: int


class BulkCategoryRequest(BaseModel):
    content_hashes: list[str] = Field(..., max_length=500)
    category_id: int


class FolderTagRequest(BaseModel):
    folder: str
    tag_id: int


class FolderCategoryRequest(BaseModel):
    folder: str
    category_id: int


class FilePathRequest(BaseModel):
    path: str


def create_bulk_router(*, tag_service: TagService, images_root: str) -> APIRouter:
    router = APIRouter()
    root_path = Path(images_root).resolve()

    # --- Folder listing ---

    @router.get("/api/folders")
    def list_folders():
        return tag_service._repo.list_folders(images_root)

    # --- Bulk by selection ---

    @router.post("/api/bulk/tags/add")
    def bulk_add_tag(body: BulkTagRequest):
        try:
            affected = tag_service.bulk_add_tag(body.content_hashes, body.tag_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/tags/remove")
    def bulk_remove_tag(body: BulkTagRequest):
        try:
            affected = tag_service.bulk_remove_tag(body.content_hashes, body.tag_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/categories/add")
    def bulk_add_category(body: BulkCategoryRequest):
        try:
            affected = tag_service.bulk_add_category(body.content_hashes, body.category_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/categories/remove")
    def bulk_remove_category(body: BulkCategoryRequest):
        try:
            affected = tag_service.bulk_remove_category(body.content_hashes, body.category_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    # --- Bulk by folder ---

    @router.post("/api/bulk/folder/tags/add")
    def bulk_folder_add_tag(body: FolderTagRequest):
        try:
            affected = tag_service.bulk_folder_add_tag(body.folder, body.tag_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/tags/remove")
    def bulk_folder_remove_tag(body: FolderTagRequest):
        try:
            affected = tag_service.bulk_folder_remove_tag(body.folder, body.tag_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/categories/add")
    def bulk_folder_add_category(body: FolderCategoryRequest):
        try:
            affected = tag_service.bulk_folder_add_category(body.folder, body.category_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    @router.post("/api/bulk/folder/categories/remove")
    def bulk_folder_remove_category(body: FolderCategoryRequest):
        try:
            affected = tag_service.bulk_folder_remove_category(body.folder, body.category_id, images_root)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "affected": affected}

    # --- File operations ---

    def _validate_file_path(file_path: str) -> Path:
        resolved = Path(file_path).resolve()
        if not resolved.is_relative_to(root_path):
            raise HTTPException(status_code=400, detail="Path is outside images root")
        if not resolved.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return resolved

    @router.post("/api/files/open")
    async def open_file(body: FilePathRequest):
        resolved = _validate_file_path(body.path)
        try:
            if sys.platform == "darwin":
                cmd = ["open", str(resolved)]
            else:
                cmd = ["xdg-open", str(resolved)]
            await asyncio.to_thread(subprocess.run, cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise HTTPException(status_code=500, detail="File operation not available in this environment")
        return {"ok": True}

    @router.post("/api/files/reveal")
    async def reveal_file(body: FilePathRequest):
        resolved = _validate_file_path(body.path)
        try:
            if sys.platform == "darwin":
                cmd = ["open", "-R", str(resolved)]
            else:
                cmd = ["xdg-open", str(resolved.parent)]
            await asyncio.to_thread(subprocess.run, cmd, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise HTTPException(status_code=500, detail="File operation not available in this environment")
        return {"ok": True}

    return router
```

- [ ] **Step 4: Register bulk router in `app.py`**

In `src/image_vector_search/app.py`, add import at top:

```python
from image_vector_search.api.bulk_routes import create_bulk_router
```

Add after the existing `create_tag_router` registration (line 64), before `dist_dir`:

```python
    if runtime_services is not None:
        app.include_router(
            create_bulk_router(
                tag_service=runtime_services.tag_service,
                images_root=str(app_settings.images_root),
            )
        )
```

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/integration/test_bulk_api.py -v`
Expected: ALL PASS

- [ ] **Step 6: Run full test suite**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add src/image_vector_search/frontend/bulk_routes.py src/image_vector_search/app.py tests/integration/test_bulk_api.py
git commit -m "feat: add HTTP routes for bulk operations, folder listing, and file open/reveal"
```

---

### Task 6: Frontend API Hooks

**Files:**
- Create: `src/image_vector_search/frontend/src/api/bulk.ts`
- Modify: `src/image_vector_search/frontend/src/api/images.ts`
- Modify: `src/image_vector_search/frontend/src/api/types.ts`

Add all React Query hooks for bulk operations, folder listing, and file operations.

- [ ] **Step 1: Add `BulkResponse` type**

In `src/image_vector_search/frontend/src/api/types.ts`, add at the end:

```typescript
export interface BulkResponse {
  ok: boolean;
  affected: number;
}
```

- [ ] **Step 2: Update `useImages` to accept folder param**

In `src/image_vector_search/frontend/src/api/images.ts`, change `useImages`:

```typescript
export function useImages(folder?: string) {
  return useQuery({
    queryKey: ["images", folder ?? "all"],
    queryFn: () => {
      const params = folder ? `?folder=${encodeURIComponent(folder)}` : "";
      return apiFetch<ImageRecord[]>(`/api/images${params}`);
    },
  });
}
```

- [ ] **Step 3: Create `bulk.ts` with all hooks**

Create `src/image_vector_search/frontend/src/api/bulk.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { BulkResponse } from "./types";

// --- Folder listing ---

export function useFolders() {
  return useQuery({
    queryKey: ["folders"],
    queryFn: () => apiFetch<string[]>("/api/folders"),
  });
}

// --- Bulk by selection ---

export function useBulkAddTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contentHashes, tagId }: { contentHashes: string[]; tagId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/tags/add", {
        method: "POST",
        body: JSON.stringify({ content_hashes: contentHashes, tag_id: tagId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkRemoveTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contentHashes, tagId }: { contentHashes: string[]; tagId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/tags/remove", {
        method: "POST",
        body: JSON.stringify({ content_hashes: contentHashes, tag_id: tagId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkAddCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contentHashes, categoryId }: { contentHashes: string[]; categoryId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/categories/add", {
        method: "POST",
        body: JSON.stringify({ content_hashes: contentHashes, category_id: categoryId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkRemoveCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ contentHashes, categoryId }: { contentHashes: string[]; categoryId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/categories/remove", {
        method: "POST",
        body: JSON.stringify({ content_hashes: contentHashes, category_id: categoryId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

// --- Bulk by folder ---

export function useBulkFolderAddTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ folder, tagId }: { folder: string; tagId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/tags/add", {
        method: "POST",
        body: JSON.stringify({ folder, tag_id: tagId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkFolderRemoveTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ folder, tagId }: { folder: string; tagId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/tags/remove", {
        method: "POST",
        body: JSON.stringify({ folder, tag_id: tagId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkFolderAddCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ folder, categoryId }: { folder: string; categoryId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/categories/add", {
        method: "POST",
        body: JSON.stringify({ folder, category_id: categoryId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export function useBulkFolderRemoveCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ folder, categoryId }: { folder: string; categoryId: number }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/categories/remove", {
        method: "POST",
        body: JSON.stringify({ folder, category_id: categoryId }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

// --- File operations ---

export function useOpenFile() {
  return useMutation({
    mutationFn: (path: string) =>
      apiFetch<{ ok: boolean }>("/api/files/open", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
  });
}

export function useRevealFile() {
  return useMutation({
    mutationFn: (path: string) =>
      apiFetch<{ ok: boolean }>("/api/files/reveal", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
  });
}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd src/image_vector_search/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/api/bulk.ts src/image_vector_search/frontend/src/api/images.ts src/image_vector_search/frontend/src/api/types.ts
git commit -m "feat: add frontend API hooks for bulk ops, folders, and file operations"
```

---

### Task 7: Frontend Images Page — Folder Filter & File Buttons

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/ImagesPage.tsx`

Add folder filter dropdown at top, and open/reveal icon buttons per row. This is the simpler UI change before the bulk action bar.

- [ ] **Step 1: Update ImagesPage with folder filter and file buttons**

Replace `src/image_vector_search/frontend/src/pages/ImagesPage.tsx` with:

```tsx
import React, { useState } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useImages } from "@/api/images";
import { useFolders, useOpenFile, useRevealFile } from "@/api/bulk";
import ImageTagEditor from "@/components/ImageTagEditor";
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  FileSearch,
} from "lucide-react";

export default function ImagesPage() {
  const [selectedFolder, setSelectedFolder] = useState<string | undefined>(
    undefined,
  );
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  const { data: folders } = useFolders();
  const { data: images, isLoading } = useImages(selectedFolder);
  const openFile = useOpenFile();
  const revealFile = useRevealFile();

  const toggleExpand = (hash: string) => {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  };

  const handleOpenFile = (e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    openFile.mutate(path, {
      onError: () => toast.error("Could not open file. Try copying the path manually."),
    });
  };

  const handleRevealFile = (e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    revealFile.mutate(path, {
      onError: () => toast.error("Could not reveal file. Try copying the path manually."),
    });
  };

  const handleFolderChange = (value: string) => {
    setSelectedFolder(value === "__all__" ? undefined : value);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Images</h1>
      </div>

      {/* Folder filter */}
      <div className="flex items-center gap-3">
        <Select
          value={selectedFolder ?? "__all__"}
          onValueChange={handleFolderChange}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="All folders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All folders</SelectItem>
            {(folders ?? []).map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground p-4">Loading...</p>
          ) : !images || images.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4">
              No images indexed yet
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Content Hash</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead className="w-20">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((image) => (
                  <React.Fragment key={image.content_hash}>
                    <TableRow
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleExpand(image.content_hash)}
                    >
                      <TableCell>
                        {expandedHash === image.content_hash ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {image.content_hash.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {image.canonical_path}
                      </TableCell>
                      <TableCell className="text-sm">
                        {image.mime_type}
                      </TableCell>
                      <TableCell className="text-sm">
                        {image.width}x{image.height}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            title="Open file"
                            onClick={(e) =>
                              handleOpenFile(e, image.canonical_path)
                            }
                          >
                            <FileSearch className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            title="Reveal in file manager"
                            onClick={(e) =>
                              handleRevealFile(e, image.canonical_path)
                            }
                          >
                            <FolderOpen className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {expandedHash === image.content_hash && (
                      <TableRow>
                        <TableCell colSpan={6} className="bg-muted/30 p-0">
                          <ImageTagEditor
                            contentHash={image.content_hash}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd src/image_vector_search/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Verify build succeeds**

Run: `cd src/image_vector_search/frontend && npm run build`
Expected: Build completes successfully

- [ ] **Step 4: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/ImagesPage.tsx
git commit -m "feat: add folder filter and file open/reveal buttons to Images page"
```

---

### Task 8: Frontend Images Page — Checkbox Selection & Bulk Action Bar

**Files:**
- Modify: `src/image_vector_search/frontend/src/pages/ImagesPage.tsx`

Add checkbox selection, floating bulk action bar, and folder quick actions dialog.

- [ ] **Step 1: Update ImagesPage with checkboxes and bulk action bar**

Replace `src/image_vector_search/frontend/src/pages/ImagesPage.tsx` with the full version that adds:
- Checkbox column with select-all in header
- `selectedHashes` state (Set)
- Floating bulk action bar at bottom when selection is active
- "Folder Actions" button + dialog for folder-level bulk ops

```tsx
import React, { useState, useMemo } from "react";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useImages } from "@/api/images";
import {
  useFolders,
  useOpenFile,
  useRevealFile,
  useBulkAddTag,
  useBulkRemoveTag,
  useBulkAddCategory,
  useBulkRemoveCategory,
  useBulkFolderAddTag,
  useBulkFolderRemoveTag,
  useBulkFolderAddCategory,
  useBulkFolderRemoveCategory,
} from "@/api/bulk";
import { useTags } from "@/api/tags";
import { useCategories } from "@/api/categories";
import ImageTagEditor from "@/components/ImageTagEditor";
import type { CategoryNode } from "@/api/types";
import {
  ChevronRight,
  ChevronDown,
  FolderOpen,
  FileSearch,
  Settings2,
} from "lucide-react";

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; label: string }[] {
  const result: { id: number; label: string }[] = [];
  for (const node of nodes) {
    result.push({
      id: node.id,
      label: "\u00A0\u00A0".repeat(depth) + node.name,
    });
    result.push(...flattenCategories(node.children, depth + 1));
  }
  return result;
}

export default function ImagesPage() {
  const [selectedFolder, setSelectedFolder] = useState<string | undefined>(
    undefined,
  );
  const [expandedHash, setExpandedHash] = useState<string | null>(null);
  const [selectedHashes, setSelectedHashes] = useState<Set<string>>(new Set());
  const [bulkTagId, setBulkTagId] = useState<string>("");
  const [bulkCategoryId, setBulkCategoryId] = useState<string>("");
  const [folderTagId, setFolderTagId] = useState<string>("");
  const [folderCategoryId, setFolderCategoryId] = useState<string>("");
  const [folderDialogOpen, setFolderDialogOpen] = useState(false);

  const { data: folders } = useFolders();
  const { data: images, isLoading } = useImages(selectedFolder);
  const { data: allTags } = useTags();
  const { data: allCategories } = useCategories();
  const openFile = useOpenFile();
  const revealFile = useRevealFile();
  const bulkAddTag = useBulkAddTag();
  const bulkRemoveTag = useBulkRemoveTag();
  const bulkAddCategory = useBulkAddCategory();
  const bulkRemoveCategory = useBulkRemoveCategory();
  const folderAddTag = useBulkFolderAddTag();
  const folderRemoveTag = useBulkFolderRemoveTag();
  const folderAddCategory = useBulkFolderAddCategory();
  const folderRemoveCategory = useBulkFolderRemoveCategory();

  const flatCategories = useMemo(
    () => flattenCategories(allCategories ?? []),
    [allCategories],
  );

  const allHashes = useMemo(
    () => (images ?? []).map((img) => img.content_hash),
    [images],
  );

  const allSelected =
    allHashes.length > 0 && allHashes.every((h) => selectedHashes.has(h));

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedHashes(new Set());
    } else {
      setSelectedHashes(new Set(allHashes));
    }
  };

  const toggleSelect = (hash: string) => {
    setSelectedHashes((prev) => {
      const next = new Set(prev);
      if (next.has(hash)) {
        next.delete(hash);
      } else {
        next.add(hash);
      }
      return next;
    });
  };

  const toggleExpand = (hash: string) => {
    setExpandedHash((prev) => (prev === hash ? null : hash));
  };

  const handleOpenFile = (e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    openFile.mutate(path, {
      onError: () =>
        toast.error("Could not open file. Try copying the path manually."),
    });
  };

  const handleRevealFile = (e: React.MouseEvent, path: string) => {
    e.stopPropagation();
    revealFile.mutate(path, {
      onError: () =>
        toast.error("Could not reveal file. Try copying the path manually."),
    });
  };

  const handleFolderChange = (value: string) => {
    setSelectedFolder(value === "__all__" ? undefined : value);
    setSelectedHashes(new Set());
  };

  const selectedArray = Array.from(selectedHashes);

  const handleBulkAddTag = () => {
    if (!bulkTagId) return;
    bulkAddTag.mutate(
      { contentHashes: selectedArray, tagId: parseInt(bulkTagId, 10) },
      {
        onSuccess: (data) => {
          toast.success(`Tag added to ${data.affected} images`);
          setSelectedHashes(new Set());
          setBulkTagId("");
        },
        onError: () => toast.error("Failed to add tag"),
      },
    );
  };

  const handleBulkRemoveTag = () => {
    if (!bulkTagId) return;
    bulkRemoveTag.mutate(
      { contentHashes: selectedArray, tagId: parseInt(bulkTagId, 10) },
      {
        onSuccess: (data) => {
          toast.success(`Tag removed from ${data.affected} images`);
          setSelectedHashes(new Set());
          setBulkTagId("");
        },
        onError: () => toast.error("Failed to remove tag"),
      },
    );
  };

  const handleBulkAddCategory = () => {
    if (!bulkCategoryId) return;
    bulkAddCategory.mutate(
      {
        contentHashes: selectedArray,
        categoryId: parseInt(bulkCategoryId, 10),
      },
      {
        onSuccess: (data) => {
          toast.success(`Category added to ${data.affected} images`);
          setSelectedHashes(new Set());
          setBulkCategoryId("");
        },
        onError: () => toast.error("Failed to add category"),
      },
    );
  };

  const handleBulkRemoveCategory = () => {
    if (!bulkCategoryId) return;
    bulkRemoveCategory.mutate(
      {
        contentHashes: selectedArray,
        categoryId: parseInt(bulkCategoryId, 10),
      },
      {
        onSuccess: (data) => {
          toast.success(`Category removed from ${data.affected} images`);
          setSelectedHashes(new Set());
          setBulkCategoryId("");
        },
        onError: () => toast.error("Failed to remove category"),
      },
    );
  };

  // Folder bulk actions
  const handleFolderAddTag = () => {
    if (!folderTagId || !selectedFolder) return;
    folderAddTag.mutate(
      { folder: selectedFolder, tagId: parseInt(folderTagId, 10) },
      {
        onSuccess: (data) => {
          toast.success(`Tag added to ${data.affected} images in folder`);
          setFolderTagId("");
        },
        onError: () => toast.error("Failed to add tag to folder"),
      },
    );
  };

  const handleFolderRemoveTag = () => {
    if (!folderTagId || !selectedFolder) return;
    folderRemoveTag.mutate(
      { folder: selectedFolder, tagId: parseInt(folderTagId, 10) },
      {
        onSuccess: (data) => {
          toast.success(`Tag removed from ${data.affected} images in folder`);
          setFolderTagId("");
        },
        onError: () => toast.error("Failed to remove tag from folder"),
      },
    );
  };

  const handleFolderAddCategory = () => {
    if (!folderCategoryId || !selectedFolder) return;
    folderAddCategory.mutate(
      {
        folder: selectedFolder,
        categoryId: parseInt(folderCategoryId, 10),
      },
      {
        onSuccess: (data) => {
          toast.success(
            `Category added to ${data.affected} images in folder`,
          );
          setFolderCategoryId("");
        },
        onError: () => toast.error("Failed to add category to folder"),
      },
    );
  };

  const handleFolderRemoveCategory = () => {
    if (!folderCategoryId || !selectedFolder) return;
    folderRemoveCategory.mutate(
      {
        folder: selectedFolder,
        categoryId: parseInt(folderCategoryId, 10),
      },
      {
        onSuccess: (data) => {
          toast.success(
            `Category removed from ${data.affected} images in folder`,
          );
          setFolderCategoryId("");
        },
        onError: () => toast.error("Failed to remove category from folder"),
      },
    );
  };

  return (
    <div className="space-y-6 pb-20">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Images</h1>
      </div>

      {/* Folder filter + folder actions */}
      <div className="flex items-center gap-3">
        <Select
          value={selectedFolder ?? "__all__"}
          onValueChange={handleFolderChange}
        >
          <SelectTrigger className="w-64">
            <SelectValue placeholder="All folders" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">All folders</SelectItem>
            {(folders ?? []).map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {selectedFolder && (
          <Dialog open={folderDialogOpen} onOpenChange={setFolderDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Settings2 className="h-4 w-4 mr-1" />
                Folder Actions
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  Folder Actions: {selectedFolder}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                {/* Tag operations */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">Tags</p>
                  <div className="flex items-center gap-2">
                    <Select
                      value={folderTagId}
                      onValueChange={setFolderTagId}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Select tag..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(allTags ?? []).map((tag) => (
                          <SelectItem key={tag.id} value={String(tag.id)}>
                            {tag.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={handleFolderAddTag}
                      disabled={!folderTagId}
                    >
                      Add
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleFolderRemoveTag}
                      disabled={!folderTagId}
                    >
                      Remove
                    </Button>
                  </div>
                </div>

                {/* Category operations */}
                <div className="space-y-2">
                  <p className="text-sm font-medium">Categories</p>
                  <div className="flex items-center gap-2">
                    <Select
                      value={folderCategoryId}
                      onValueChange={setFolderCategoryId}
                    >
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Select category..." />
                      </SelectTrigger>
                      <SelectContent>
                        {flatCategories.map((cat) => (
                          <SelectItem key={cat.id} value={String(cat.id)}>
                            {cat.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      size="sm"
                      onClick={handleFolderAddCategory}
                      disabled={!folderCategoryId}
                    >
                      Add
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleFolderRemoveCategory}
                      disabled={!folderCategoryId}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="text-sm text-muted-foreground p-4">Loading...</p>
          ) : !images || images.length === 0 ? (
            <p className="text-sm text-muted-foreground p-4">
              No images indexed yet
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <Checkbox
                      checked={allSelected}
                      onCheckedChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead className="w-8" />
                  <TableHead>Content Hash</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead className="w-20">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((image) => (
                  <React.Fragment key={image.content_hash}>
                    <TableRow
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => toggleExpand(image.content_hash)}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          checked={selectedHashes.has(image.content_hash)}
                          onCheckedChange={() =>
                            toggleSelect(image.content_hash)
                          }
                        />
                      </TableCell>
                      <TableCell>
                        {expandedHash === image.content_hash ? (
                          <ChevronDown className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {image.content_hash.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground max-w-xs truncate">
                        {image.canonical_path}
                      </TableCell>
                      <TableCell className="text-sm">
                        {image.mime_type}
                      </TableCell>
                      <TableCell className="text-sm">
                        {image.width}x{image.height}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            title="Open file"
                            onClick={(e) =>
                              handleOpenFile(e, image.canonical_path)
                            }
                          >
                            <FileSearch className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            title="Reveal in file manager"
                            onClick={(e) =>
                              handleRevealFile(e, image.canonical_path)
                            }
                          >
                            <FolderOpen className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {expandedHash === image.content_hash && (
                      <TableRow>
                        <TableCell colSpan={7} className="bg-muted/30 p-0">
                          <ImageTagEditor
                            contentHash={image.content_hash}
                          />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Floating bulk action bar */}
      {selectedHashes.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 bg-background border-t shadow-lg p-4 z-50">
          <div className="max-w-5xl mx-auto flex items-center gap-4 flex-wrap">
            <span className="text-sm font-medium">
              {selectedHashes.size} selected
            </span>

            {/* Tag actions */}
            <Select value={bulkTagId} onValueChange={setBulkTagId}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Tag..." />
              </SelectTrigger>
              <SelectContent>
                {(allTags ?? []).map((tag) => (
                  <SelectItem key={tag.id} value={String(tag.id)}>
                    {tag.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              onClick={handleBulkAddTag}
              disabled={!bulkTagId}
            >
              Add Tag
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleBulkRemoveTag}
              disabled={!bulkTagId}
            >
              Remove Tag
            </Button>

            <div className="w-px h-6 bg-border" />

            {/* Category actions */}
            <Select value={bulkCategoryId} onValueChange={setBulkCategoryId}>
              <SelectTrigger className="w-36">
                <SelectValue placeholder="Category..." />
              </SelectTrigger>
              <SelectContent>
                {flatCategories.map((cat) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              onClick={handleBulkAddCategory}
              disabled={!bulkCategoryId}
            >
              Add Category
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleBulkRemoveCategory}
              disabled={!bulkCategoryId}
            >
              Remove Category
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
```

**Note:** This requires the `Checkbox` and `Dialog` shadcn/ui components. If not already installed, run:
```bash
cd src/image_vector_search/frontend && npx shadcn@latest add checkbox dialog
```

- [ ] **Step 2: Install missing shadcn/ui components if needed**

Run: `cd src/image_vector_search/frontend && npx shadcn@latest add checkbox dialog`
Expected: Components added to `src/components/ui/`

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd src/image_vector_search/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Verify build succeeds**

Run: `cd src/image_vector_search/frontend && npm run build`
Expected: Build completes successfully

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/frontend/
git commit -m "feat: add checkbox selection, bulk action bar, and folder actions to Images page"
```

---

### Task 9: End-to-End Verification

**Files:**
- No new files

Final verification that everything works together.

- [ ] **Step 1: Run full Python test suite**

Run: `pytest -v`
Expected: ALL PASS

- [ ] **Step 2: Build frontend**

Run: `cd src/image_vector_search/frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Run TypeScript checks**

Run: `cd src/image_vector_search/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 4: Verify all new endpoints exist**

Start the server (manual verification):
```bash
uvicorn image_vector_search.app:create_app --factory --port 8000
```
Then verify endpoints respond:
- `GET /api/folders` → 200
- `POST /api/bulk/tags/add` → accepts JSON body
- `POST /api/files/open` → validates path
- Frontend at `http://localhost:8000/images` shows folder filter, checkboxes, bulk bar

- [ ] **Step 5: Final commit if any fixups needed**

```bash
git add -A && git commit -m "fix: address any remaining issues from end-to-end verification"
```
