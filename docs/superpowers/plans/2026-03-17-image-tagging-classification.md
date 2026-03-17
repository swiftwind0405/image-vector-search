# Image Tagging & Classification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual tagging and hierarchical classification to the image search service, with combination filtering on vector search.

**Architecture:** Extend SQLite schema with tags/categories/join tables. Add repository methods, a thin TagService, and REST endpoints. Extend VectorIndex.search() to accept content_hash pre-filter for combination queries.

**Tech Stack:** SQLite, Pydantic, FastAPI, pytest, Milvus Lite

**Spec:** `docs/superpowers/specs/2026-03-17-image-tagging-classification-design.md`

---

### Task 1: Domain Models

**Files:**
- Modify: `src/image_search_mcp/domain/models.py`
- Test: `tests/unit/test_domain_models.py`

- [ ] **Step 1: Write test for new domain models**

```python
# Append to tests/unit/test_domain_models.py

from image_search_mcp.domain.models import Tag, Category, CategoryNode
from datetime import datetime, timezone


class TestTag:
    def test_create_tag(self):
        tag = Tag(id=1, name="sunset", created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert tag.id == 1
        assert tag.name == "sunset"


class TestCategory:
    def test_create_root_category(self):
        cat = Category(id=1, name="Nature", parent_id=None, sort_order=0, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert cat.parent_id is None

    def test_create_child_category(self):
        cat = Category(id=2, name="Flowers", parent_id=1, sort_order=0, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert cat.parent_id == 1


class TestCategoryNode:
    def test_tree_structure(self):
        child = CategoryNode(id=2, name="Flowers", parent_id=1, sort_order=0, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        root = CategoryNode(id=1, name="Nature", parent_id=None, sort_order=0, created_at=datetime(2026, 1, 1, tzinfo=timezone.utc), children=[child])
        assert len(root.children) == 1
        assert root.children[0].name == "Flowers"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_domain_models.py::TestTag -v`
Expected: ImportError — `Tag` not defined

- [ ] **Step 3: Add domain models to models.py**

Add to `src/image_search_mcp/domain/models.py`:

```python
class Tag(BaseModel):
    id: int
    name: str
    created_at: datetime

class Category(BaseModel):
    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: datetime

class CategoryNode(BaseModel):
    """Category with children, for tree responses."""
    id: int
    name: str
    parent_id: int | None
    sort_order: int
    created_at: datetime
    children: list["CategoryNode"] = []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_domain_models.py::TestTag tests/unit/test_domain_models.py::TestCategory tests/unit/test_domain_models.py::TestCategoryNode -v`
Expected: 4 PASS

- [ ] **Step 5: Extend SearchResult with tags and categories fields**

In `src/image_search_mcp/domain/models.py`, add to `SearchResult`:

```python
class SearchResult(BaseModel):
    content_hash: str
    path: str
    score: float
    width: int
    height: int
    mime_type: str
    tags: list[Tag] = []
    categories: list[Category] = []
```

- [ ] **Step 6: Run all domain model tests**

Run: `pytest tests/unit/test_domain_models.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/image_search_mcp/domain/models.py tests/unit/test_domain_models.py
git commit -m "feat: add Tag, Category, CategoryNode domain models and extend SearchResult"
```

---

### Task 2: Database Schema

**Files:**
- Modify: `src/image_search_mcp/repositories/schema.sql`
- Test: `tests/unit/test_sqlite_repository.py`

- [ ] **Step 1: Write test for schema creation**

Add to `tests/unit/test_sqlite_repository.py`:

```python
class TestTaggingSchema:
    def test_tags_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
            assert cursor.fetchone() is not None

    def test_categories_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
            assert cursor.fetchone() is not None

    def test_image_tags_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_tags'")
            assert cursor.fetchone() is not None

    def test_image_tags_check_constraint(self, tmp_path):
        """Both tag_id and category_id NULL should fail."""
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            conn.execute("INSERT INTO tags (name, created_at) VALUES ('test', '2026-01-01T00:00:00+00:00')")
            # Insert a dummy image first
            conn.execute("""
                INSERT INTO images (content_hash, canonical_path, file_size, mtime, mime_type,
                    width, height, is_active, last_seen_at, embedding_provider, embedding_model,
                    embedding_version, created_at, updated_at)
                VALUES ('abc123', '/test.jpg', 100, 1.0, 'image/jpeg', 100, 100, 1,
                    '2026-01-01T00:00:00+00:00', 'jina', 'jina-clip-v2', 'v2',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """)
            # Should succeed: tag_id set, category_id NULL
            conn.execute("""
                INSERT INTO image_tags (content_hash, tag_id, category_id, created_at)
                VALUES ('abc123', 1, NULL, '2026-01-01T00:00:00+00:00')
            """)
            # Should fail: both NULL
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO image_tags (content_hash, tag_id, category_id, created_at)
                    VALUES ('abc123', NULL, NULL, '2026-01-01T00:00:00+00:00')
                """)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sqlite_repository.py::TestTaggingSchema -v`
Expected: FAIL — tables don't exist

- [ ] **Step 3: Add DDL to schema.sql**

Append to `src/image_search_mcp/repositories/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES categories(id),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    UNIQUE(parent_id, name)
);

CREATE TABLE IF NOT EXISTS image_tags (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash  TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    tag_id        INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    category_id   INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    UNIQUE(content_hash, tag_id),
    UNIQUE(content_hash, category_id),
    CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_image_tags_content_hash ON image_tags(content_hash);
CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_image_tags_category_id ON image_tags(category_id);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sqlite_repository.py::TestTaggingSchema -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_search_mcp/repositories/schema.sql tests/unit/test_sqlite_repository.py
git commit -m "feat: add tags, categories, image_tags tables to schema"
```

---

### Task 3: Repository — Tag CRUD

**Files:**
- Modify: `src/image_search_mcp/repositories/sqlite.py`
- Test: `tests/unit/test_sqlite_repository.py`

- [ ] **Step 1: Write tests for tag CRUD**

Add to `tests/unit/test_sqlite_repository.py`:

```python
from image_search_mcp.domain.models import Tag


class TestTagCRUD:
    def _make_repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        return repo

    def test_create_tag(self, tmp_path):
        repo = self._make_repo(tmp_path)
        tag = repo.create_tag("sunset")
        assert tag.name == "sunset"
        assert tag.id is not None

    def test_create_duplicate_tag_raises(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.create_tag("sunset")
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            repo.create_tag("sunset")

    def test_list_tags(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.create_tag("sunset")
        repo.create_tag("beach")
        tags = repo.list_tags()
        assert len(tags) == 2
        names = {t.name for t in tags}
        assert names == {"sunset", "beach"}

    def test_list_tags_empty(self, tmp_path):
        repo = self._make_repo(tmp_path)
        assert repo.list_tags() == []

    def test_rename_tag(self, tmp_path):
        repo = self._make_repo(tmp_path)
        tag = repo.create_tag("sunset")
        repo.rename_tag(tag.id, "sunrise")
        tags = repo.list_tags()
        assert tags[0].name == "sunrise"

    def test_delete_tag(self, tmp_path):
        repo = self._make_repo(tmp_path)
        tag = repo.create_tag("sunset")
        repo.delete_tag(tag.id)
        assert repo.list_tags() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sqlite_repository.py::TestTagCRUD -v`
Expected: FAIL — methods not defined

- [ ] **Step 3: Implement tag CRUD in MetadataRepository**

Add to `src/image_search_mcp/repositories/sqlite.py`:

```python
def create_tag(self, name: str) -> Tag:
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        cursor = conn.execute(
            "INSERT INTO tags (name, created_at) VALUES (?, ?)",
            (name, now),
        )
        return Tag(id=cursor.lastrowid, name=name, created_at=_from_iso(now))

def list_tags(self) -> list[Tag]:
    with self.connect() as conn:
        rows = conn.execute("SELECT id, name, created_at FROM tags ORDER BY name").fetchall()
        return [Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"])) for r in rows]

def rename_tag(self, tag_id: int, new_name: str) -> None:
    with self.connect() as conn:
        conn.execute("UPDATE tags SET name = ? WHERE id = ?", (new_name, tag_id))

def delete_tag(self, tag_id: int) -> None:
    with self.connect() as conn:
        conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
```

Add `Tag` to the imports from `domain.models` at the top of `sqlite.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sqlite_repository.py::TestTagCRUD -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_search_mcp/repositories/sqlite.py tests/unit/test_sqlite_repository.py
git commit -m "feat: add tag CRUD to MetadataRepository"
```

---

### Task 4: Repository — Category CRUD

**Files:**
- Modify: `src/image_search_mcp/repositories/sqlite.py`
- Test: `tests/unit/test_sqlite_repository.py`

- [ ] **Step 1: Write tests for category CRUD**

Add to `tests/unit/test_sqlite_repository.py`:

```python
from image_search_mcp.domain.models import Category, CategoryNode


class TestCategoryCRUD:
    def _make_repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        return repo

    def test_create_root_category(self, tmp_path):
        repo = self._make_repo(tmp_path)
        cat = repo.create_category("Nature")
        assert cat.name == "Nature"
        assert cat.parent_id is None

    def test_create_child_category(self, tmp_path):
        repo = self._make_repo(tmp_path)
        parent = repo.create_category("Nature")
        child = repo.create_category("Flowers", parent_id=parent.id)
        assert child.parent_id == parent.id

    def test_duplicate_name_under_same_parent_raises(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.create_category("Nature")
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            repo.create_category("Nature")  # same parent (None)

    def test_same_name_different_parent_ok(self, tmp_path):
        repo = self._make_repo(tmp_path)
        p1 = repo.create_category("Work")
        p2 = repo.create_category("Personal")
        repo.create_category("Photos", parent_id=p1.id)
        repo.create_category("Photos", parent_id=p2.id)  # should not raise

    def test_list_categories_root(self, tmp_path):
        repo = self._make_repo(tmp_path)
        repo.create_category("Nature")
        repo.create_category("Work")
        cats = repo.list_categories(parent_id=None)
        assert len(cats) == 2

    def test_list_categories_children(self, tmp_path):
        repo = self._make_repo(tmp_path)
        parent = repo.create_category("Nature")
        repo.create_category("Flowers", parent_id=parent.id)
        repo.create_category("Mountains", parent_id=parent.id)
        children = repo.list_categories(parent_id=parent.id)
        assert len(children) == 2

    def test_get_category_tree(self, tmp_path):
        repo = self._make_repo(tmp_path)
        nature = repo.create_category("Nature")
        repo.create_category("Flowers", parent_id=nature.id)
        work = repo.create_category("Work")
        tree = repo.get_category_tree()
        assert len(tree) == 2  # two root nodes
        nature_node = next(n for n in tree if n.name == "Nature")
        assert len(nature_node.children) == 1
        work_node = next(n for n in tree if n.name == "Work")
        assert len(work_node.children) == 0

    def test_rename_category(self, tmp_path):
        repo = self._make_repo(tmp_path)
        cat = repo.create_category("Nature")
        repo.rename_category(cat.id, "Outdoors")
        cats = repo.list_categories()
        assert cats[0].name == "Outdoors"

    def test_move_category(self, tmp_path):
        repo = self._make_repo(tmp_path)
        a = repo.create_category("A")
        b = repo.create_category("B")
        child = repo.create_category("Child", parent_id=a.id)
        repo.move_category(child.id, b.id)
        children_of_b = repo.list_categories(parent_id=b.id)
        assert len(children_of_b) == 1
        assert children_of_b[0].name == "Child"

    def test_delete_category_cascades_children(self, tmp_path):
        repo = self._make_repo(tmp_path)
        parent = repo.create_category("Nature")
        repo.create_category("Flowers", parent_id=parent.id)
        repo.delete_category(parent.id)
        assert repo.list_categories() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sqlite_repository.py::TestCategoryCRUD -v`
Expected: FAIL — methods not defined

- [ ] **Step 3: Implement category CRUD in MetadataRepository**

Add to `src/image_search_mcp/repositories/sqlite.py`:

```python
def create_category(self, name: str, parent_id: int | None = None) -> Category:
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        cursor = conn.execute(
            "INSERT INTO categories (name, parent_id, sort_order, created_at) VALUES (?, ?, 0, ?)",
            (name, parent_id, now),
        )
        return Category(
            id=cursor.lastrowid, name=name, parent_id=parent_id,
            sort_order=0, created_at=_from_iso(now),
        )

def list_categories(self, parent_id: int | None = None) -> list[Category]:
    with self.connect() as conn:
        if parent_id is None:
            rows = conn.execute(
                "SELECT id, name, parent_id, sort_order, created_at FROM categories WHERE parent_id IS NULL ORDER BY sort_order, name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, parent_id, sort_order, created_at FROM categories WHERE parent_id = ? ORDER BY sort_order, name",
                (parent_id,),
            ).fetchall()
        return [self._row_to_category(r) for r in rows]

def get_category_tree(self) -> list[CategoryNode]:
    with self.connect() as conn:
        rows = conn.execute(
            "SELECT id, name, parent_id, sort_order, created_at FROM categories ORDER BY sort_order, name"
        ).fetchall()
    nodes: dict[int, CategoryNode] = {}
    for r in rows:
        nodes[r["id"]] = CategoryNode(
            id=r["id"], name=r["name"], parent_id=r["parent_id"],
            sort_order=r["sort_order"], created_at=_from_iso(r["created_at"]),
        )
    roots: list[CategoryNode] = []
    for node in nodes.values():
        if node.parent_id is not None and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots

def rename_category(self, category_id: int, new_name: str) -> None:
    with self.connect() as conn:
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id))

def move_category(self, category_id: int, new_parent_id: int | None) -> None:
    with self.connect() as conn:
        conn.execute("UPDATE categories SET parent_id = ? WHERE id = ?", (new_parent_id, category_id))

def delete_category(self, category_id: int) -> None:
    with self.connect() as conn:
        # Recursive CTE to find all descendants
        rows = conn.execute("""
            WITH RECURSIVE descendants(id) AS (
                SELECT id FROM categories WHERE id = ?
                UNION ALL
                SELECT c.id FROM categories c JOIN descendants d ON c.parent_id = d.id
            )
            SELECT id FROM descendants
        """, (category_id,)).fetchall()
        ids = [r["id"] for r in rows]
        if not ids:
            return
        placeholders = ",".join("?" * len(ids))
        conn.execute(f"DELETE FROM image_tags WHERE category_id IN ({placeholders})", ids)
        conn.execute(f"DELETE FROM categories WHERE id IN ({placeholders})", ids)

def _row_to_category(self, row) -> Category:
    return Category(
        id=row["id"], name=row["name"], parent_id=row["parent_id"],
        sort_order=row["sort_order"], created_at=_from_iso(row["created_at"]),
    )
```

Add `Category, CategoryNode` to the imports from `domain.models`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sqlite_repository.py::TestCategoryCRUD -v`
Expected: 10 PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_search_mcp/repositories/sqlite.py tests/unit/test_sqlite_repository.py
git commit -m "feat: add category CRUD to MetadataRepository"
```

---

### Task 5: Repository — Image Associations & Filters

**Files:**
- Modify: `src/image_search_mcp/repositories/sqlite.py`
- Test: `tests/unit/test_sqlite_repository.py`

- [ ] **Step 1: Write tests for image-tag/category associations**

Add to `tests/unit/test_sqlite_repository.py`:

```python
class TestImageAssociations:
    """Tests for adding/removing tags and categories to images, plus filter queries."""

    def _make_repo(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        return repo

    def _insert_image(self, repo, content_hash="abc123"):
        """Helper to insert a minimal image record for FK satisfaction."""
        with repo.connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO images (content_hash, canonical_path, file_size, mtime, mime_type,
                    width, height, is_active, last_seen_at, embedding_provider, embedding_model,
                    embedding_version, created_at, updated_at)
                VALUES (?, '/test.jpg', 100, 1.0, 'image/jpeg', 100, 100, 1,
                    '2026-01-01T00:00:00+00:00', 'jina', 'jina-clip-v2', 'v2',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """, (content_hash,))

    def test_add_and_get_image_tags(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo)
        tag = repo.create_tag("sunset")
        repo.add_tag_to_image("abc123", tag.id)
        tags = repo.get_image_tags("abc123")
        assert len(tags) == 1
        assert tags[0].name == "sunset"

    def test_remove_tag_from_image(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo)
        tag = repo.create_tag("sunset")
        repo.add_tag_to_image("abc123", tag.id)
        repo.remove_tag_from_image("abc123", tag.id)
        assert repo.get_image_tags("abc123") == []

    def test_add_and_get_image_categories(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo)
        cat = repo.create_category("Nature")
        repo.add_image_to_category("abc123", cat.id)
        cats = repo.get_image_categories("abc123")
        assert len(cats) == 1
        assert cats[0].name == "Nature"

    def test_remove_image_from_category(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo)
        cat = repo.create_category("Nature")
        repo.add_image_to_category("abc123", cat.id)
        repo.remove_image_from_category("abc123", cat.id)
        assert repo.get_image_categories("abc123") == []

    def test_filter_by_tags_all_match(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo, "img1")
        self._insert_image(repo, "img2")
        t1 = repo.create_tag("red")
        t2 = repo.create_tag("large")
        repo.add_tag_to_image("img1", t1.id)
        repo.add_tag_to_image("img1", t2.id)
        repo.add_tag_to_image("img2", t1.id)  # only red, not large
        result = repo.filter_by_tags([t1.id, t2.id])
        assert result == {"img1"}

    def test_filter_by_category_with_subcategories(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo, "img1")
        self._insert_image(repo, "img2")
        parent = repo.create_category("Nature")
        child = repo.create_category("Flowers", parent_id=parent.id)
        repo.add_image_to_category("img1", parent.id)
        repo.add_image_to_category("img2", child.id)
        result = repo.filter_by_category(parent.id, include_subcategories=True)
        assert result == {"img1", "img2"}

    def test_filter_by_category_without_subcategories(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo, "img1")
        self._insert_image(repo, "img2")
        parent = repo.create_category("Nature")
        child = repo.create_category("Flowers", parent_id=parent.id)
        repo.add_image_to_category("img1", parent.id)
        repo.add_image_to_category("img2", child.id)
        result = repo.filter_by_category(parent.id, include_subcategories=False)
        assert result == {"img1"}

    def test_batch_get_tags_for_images(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo, "img1")
        self._insert_image(repo, "img2")
        t1 = repo.create_tag("red")
        t2 = repo.create_tag("blue")
        repo.add_tag_to_image("img1", t1.id)
        repo.add_tag_to_image("img2", t2.id)
        result = repo.get_tags_for_images(["img1", "img2"])
        assert len(result["img1"]) == 1
        assert result["img1"][0].name == "red"
        assert result["img2"][0].name == "blue"

    def test_batch_get_categories_for_images(self, tmp_path):
        repo = self._make_repo(tmp_path)
        self._insert_image(repo, "img1")
        cat = repo.create_category("Nature")
        repo.add_image_to_category("img1", cat.id)
        result = repo.get_categories_for_images(["img1", "img2"])
        assert len(result["img1"]) == 1
        assert result.get("img2", []) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_sqlite_repository.py::TestImageAssociations -v`
Expected: FAIL — methods not defined

- [ ] **Step 3: Implement association and filter methods**

Add to `src/image_search_mcp/repositories/sqlite.py`:

```python
def add_tag_to_image(self, content_hash: str, tag_id: int) -> None:
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        conn.execute(
            "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
            (content_hash, tag_id, now),
        )

def remove_tag_from_image(self, content_hash: str, tag_id: int) -> None:
    with self.connect() as conn:
        conn.execute(
            "DELETE FROM image_tags WHERE content_hash = ? AND tag_id = ?",
            (content_hash, tag_id),
        )

def add_image_to_category(self, content_hash: str, category_id: int) -> None:
    now = _to_iso(datetime.now(timezone.utc))
    with self.connect() as conn:
        conn.execute(
            "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
            (content_hash, category_id, now),
        )

def remove_image_from_category(self, content_hash: str, category_id: int) -> None:
    with self.connect() as conn:
        conn.execute(
            "DELETE FROM image_tags WHERE content_hash = ? AND category_id = ?",
            (content_hash, category_id),
        )

def get_image_tags(self, content_hash: str) -> list[Tag]:
    with self.connect() as conn:
        rows = conn.execute("""
            SELECT t.id, t.name, t.created_at
            FROM tags t JOIN image_tags it ON t.id = it.tag_id
            WHERE it.content_hash = ?
            ORDER BY t.name
        """, (content_hash,)).fetchall()
        return [Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"])) for r in rows]

def get_image_categories(self, content_hash: str) -> list[Category]:
    with self.connect() as conn:
        rows = conn.execute("""
            SELECT c.id, c.name, c.parent_id, c.sort_order, c.created_at
            FROM categories c JOIN image_tags it ON c.id = it.category_id
            WHERE it.content_hash = ?
            ORDER BY c.name
        """, (content_hash,)).fetchall()
        return [self._row_to_category(r) for r in rows]

def get_tags_for_images(self, content_hashes: list[str]) -> dict[str, list[Tag]]:
    if not content_hashes:
        return {}
    with self.connect() as conn:
        placeholders = ",".join("?" * len(content_hashes))
        rows = conn.execute(f"""
            SELECT it.content_hash, t.id, t.name, t.created_at
            FROM tags t JOIN image_tags it ON t.id = it.tag_id
            WHERE it.content_hash IN ({placeholders})
            ORDER BY t.name
        """, content_hashes).fetchall()
    result: dict[str, list[Tag]] = {}
    for r in rows:
        tag = Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"]))
        result.setdefault(r["content_hash"], []).append(tag)
    return result

def get_categories_for_images(self, content_hashes: list[str]) -> dict[str, list[Category]]:
    if not content_hashes:
        return {}
    with self.connect() as conn:
        placeholders = ",".join("?" * len(content_hashes))
        rows = conn.execute(f"""
            SELECT it.content_hash, c.id, c.name, c.parent_id, c.sort_order, c.created_at
            FROM categories c JOIN image_tags it ON c.id = it.category_id
            WHERE it.content_hash IN ({placeholders})
            ORDER BY c.name
        """, content_hashes).fetchall()
    result: dict[str, list[Category]] = {}
    for r in rows:
        cat = self._row_to_category(r)
        result.setdefault(r["content_hash"], []).append(cat)
    return result

def filter_by_tags(self, tag_ids: list[int]) -> set[str]:
    if not tag_ids:
        return set()
    with self.connect() as conn:
        placeholders = ",".join("?" * len(tag_ids))
        rows = conn.execute(f"""
            SELECT content_hash
            FROM image_tags
            WHERE tag_id IN ({placeholders})
            GROUP BY content_hash
            HAVING COUNT(DISTINCT tag_id) = ?
        """, [*tag_ids, len(tag_ids)]).fetchall()
        return {r["content_hash"] for r in rows}

def filter_by_category(self, category_id: int, include_subcategories: bool = True) -> set[str]:
    with self.connect() as conn:
        if include_subcategories:
            rows = conn.execute("""
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM categories WHERE id = ?
                    UNION ALL
                    SELECT c.id FROM categories c JOIN descendants d ON c.parent_id = d.id
                )
                SELECT DISTINCT it.content_hash
                FROM image_tags it
                WHERE it.category_id IN (SELECT id FROM descendants)
            """, (category_id,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT DISTINCT content_hash FROM image_tags WHERE category_id = ?",
                (category_id,),
            ).fetchall()
        return {r["content_hash"] for r in rows}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_sqlite_repository.py::TestImageAssociations -v`
Expected: 9 PASS

- [ ] **Step 5: Run all repository tests**

Run: `pytest tests/unit/test_sqlite_repository.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add src/image_search_mcp/repositories/sqlite.py tests/unit/test_sqlite_repository.py
git commit -m "feat: add image-tag/category associations and filter queries"
```

---

### Task 6: VectorIndex — content_hash_filter Parameter

**Files:**
- Modify: `src/image_search_mcp/adapters/vector_index/base.py`
- Modify: `src/image_search_mcp/adapters/vector_index/milvus_lite.py`
- Modify: `tests/unit/test_search_service.py` (update `FakeVectorIndex`)
- Modify: `tests/integration/conftest.py` (update `InMemoryVectorIndex`)
- Test: `tests/unit/test_milvus_lite_index.py`

**IMPORTANT:** When changing the `VectorIndex.search()` signature, ALL implementations must be updated simultaneously to avoid breaking existing tests. This includes:
- `MilvusLiteIndex` (production)
- `FakeVectorIndex` in `tests/unit/test_search_service.py`
- `InMemoryVectorIndex` in `tests/integration/conftest.py`

- [ ] **Step 1: Update VectorIndex base class**

In `src/image_search_mcp/adapters/vector_index/base.py`, update the `search` signature:

```python
@abc.abstractmethod
def search(
    self,
    vector: list[float],
    limit: int,
    embedding_key: str,
    content_hash_filter: set[str] | None = None,
) -> list[dict]:
```

- [ ] **Step 2: Update MilvusLiteIndex.search()**

In `src/image_search_mcp/adapters/vector_index/milvus_lite.py`, update the `search` method:

```python
def search(
    self,
    vector: list[float],
    limit: int,
    embedding_key: str,
    content_hash_filter: set[str] | None = None,
) -> list[dict]:
```

Build the filter expression by combining embedding_key filter with content_hash `in` filter:

```python
filter_expr = self._embedding_filter(embedding_key)
if content_hash_filter is not None:
    escaped = [self._escape_filter_value(h) for h in content_hash_filter]
    in_list = ", ".join(f'"{v}"' for v in escaped)
    filter_expr += f" and {self._PK_FIELD} in [{in_list}]"
```

Pass `filter_expr` as the `filter` parameter to `self._client.search()`.

- [ ] **Step 3: Update FakeVectorIndex in test_search_service.py**

In `tests/unit/test_search_service.py`, update `FakeVectorIndex.search()`:

```python
def search(self, vector: list[float], limit: int, embedding_key: str,
           content_hash_filter: set[str] | None = None) -> list[dict]:
    self.requested_limits.append(limit)
    self.last_content_hash_filter = content_hash_filter  # capture for assertions
    results = self._results
    if content_hash_filter is not None:
        results = [r for r in results if r["content_hash"] in content_hash_filter]
    return results[:limit]
```

- [ ] **Step 4: Update InMemoryVectorIndex in integration conftest.py**

In `tests/integration/conftest.py`, update `InMemoryVectorIndex.search()` to accept and apply the new `content_hash_filter` parameter. Filter stored vectors by content_hash before computing similarity, following the same pattern.

- [ ] **Step 5: Write test for content_hash_filter**

Add to `tests/unit/test_milvus_lite_index.py`. Adapt to the existing test patterns in the file:

1. Insert 2+ embeddings with different content_hashes
2. Call `search()` with `content_hash_filter={"hash1"}`
3. Assert only `hash1` appears in results

- [ ] **Step 6: Run ALL tests to verify nothing is broken**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add src/image_search_mcp/adapters/vector_index/base.py src/image_search_mcp/adapters/vector_index/milvus_lite.py tests/unit/test_milvus_lite_index.py tests/unit/test_search_service.py tests/integration/conftest.py
git commit -m "feat: add content_hash_filter to VectorIndex.search()"
```

---

### Task 7: TagService

**Files:**
- Create: `src/image_search_mcp/services/tagging.py`
- Test: `tests/unit/test_tag_service.py`

- [ ] **Step 1: Write tests for TagService**

Create `tests/unit/test_tag_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from image_search_mcp.services.tagging import TagService
from image_search_mcp.domain.models import Tag, Category, CategoryNode
from datetime import datetime, timezone


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestTagServiceValidation:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    def test_create_tag_empty_name_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_tag("")

    def test_create_tag_whitespace_only_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_tag("   ")

    def test_create_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.create_tag.return_value = Tag(id=1, name="sunset", created_at=NOW)
        result = svc.create_tag("sunset")
        repo.create_tag.assert_called_once_with("sunset")
        assert result.name == "sunset"

    def test_create_category_empty_name_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_category("")

    def test_create_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.create_category.return_value = Category(
            id=1, name="Nature", parent_id=None, sort_order=0, created_at=NOW
        )
        result = svc.create_category("Nature")
        repo.create_category.assert_called_once_with("Nature", parent_id=None)
        assert result.name == "Nature"

    def test_move_category_to_self_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="itself"):
            svc.move_category(1, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_tag_service.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement TagService**

Create `src/image_search_mcp/services/tagging.py`:

```python
from __future__ import annotations

from image_search_mcp.domain.models import Tag, Category, CategoryNode
from image_search_mcp.repositories.sqlite import MetadataRepository


class TagService:
    def __init__(self, *, repository: MetadataRepository) -> None:
        self._repo = repository

    # --- Tags ---

    def create_tag(self, name: str) -> Tag:
        name = name.strip()
        if not name:
            raise ValueError("Tag name must not be empty")
        return self._repo.create_tag(name)

    def list_tags(self) -> list[Tag]:
        return self._repo.list_tags()

    def rename_tag(self, tag_id: int, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Tag name must not be empty")
        self._repo.rename_tag(tag_id, new_name)

    def delete_tag(self, tag_id: int) -> None:
        self._repo.delete_tag(tag_id)

    # --- Categories ---

    def create_category(self, name: str, parent_id: int | None = None) -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name must not be empty")
        return self._repo.create_category(name, parent_id=parent_id)

    def list_categories(self, parent_id: int | None = None) -> list[Category]:
        return self._repo.list_categories(parent_id=parent_id)

    def get_category_tree(self) -> list[CategoryNode]:
        return self._repo.get_category_tree()

    def rename_category(self, category_id: int, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Category name must not be empty")
        self._repo.rename_category(category_id, new_name)

    def move_category(self, category_id: int, new_parent_id: int | None) -> None:
        if new_parent_id == category_id:
            raise ValueError("Cannot move a category to itself")
        self._repo.move_category(category_id, new_parent_id)

    def delete_category(self, category_id: int) -> None:
        self._repo.delete_category(category_id)

    # --- Image associations ---

    def add_tag_to_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.add_tag_to_image(content_hash, tag_id)

    def remove_tag_from_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.remove_tag_from_image(content_hash, tag_id)

    def add_image_to_category(self, content_hash: str, category_id: int) -> None:
        self._repo.add_image_to_category(content_hash, category_id)

    def remove_image_from_category(self, content_hash: str, category_id: int) -> None:
        self._repo.remove_image_from_category(content_hash, category_id)

    def get_image_tags(self, content_hash: str) -> list[Tag]:
        return self._repo.get_image_tags(content_hash)

    def get_image_categories(self, content_hash: str) -> list[Category]:
        return self._repo.get_image_categories(content_hash)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_tag_service.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/image_search_mcp/services/tagging.py tests/unit/test_tag_service.py
git commit -m "feat: add TagService with input validation"
```

---

### Task 8: SearchService — Combination Filtering

**Files:**
- Modify: `src/image_search_mcp/services/search.py`
- Test: `tests/unit/test_search_service.py`

- [ ] **Step 1: Write tests for combination filtering**

Add to `tests/unit/test_search_service.py`. Extend `FakeRepository` with `filter_by_tags`, `filter_by_category`, `get_tags_for_images`, and `get_categories_for_images` methods:

```python
# Add to FakeRepository:
class FakeRepository:
    # ... existing code ...
    def __init__(self):
        # ... existing ...
        self.tag_filter_result: set[str] = set()
        self.category_filter_result: set[str] = set()
        self.tags_for_images: dict[str, list] = {}
        self.categories_for_images: dict[str, list] = {}

    def filter_by_tags(self, tag_ids: list[int]) -> set[str]:
        return self.tag_filter_result

    def filter_by_category(self, category_id: int, include_subcategories: bool = True) -> set[str]:
        return self.category_filter_result

    def get_tags_for_images(self, content_hashes: list[str]) -> dict[str, list]:
        return {h: self.tags_for_images.get(h, []) for h in content_hashes}

    def get_categories_for_images(self, content_hashes: list[str]) -> dict[str, list]:
        return {h: self.categories_for_images.get(h, []) for h in content_hashes}


class TestSearchWithTagFilter:
    """Tests for tag/category combination filtering on search."""

    @pytest.mark.anyio
    async def test_search_with_tag_filter_passes_hashes_to_vector_index(self):
        """When tag_ids provided, SearchService should query repo and pass filter."""
        repo = FakeRepository()
        repo.tag_filter_result = {"img1", "img2"}
        repo.images = {"img1": build_image_record(content_hash="img1"),
                       "img2": build_image_record(content_hash="img2")}
        vector_index = FakeVectorIndex([
            {"content_hash": "img1", "score": 0.9},
            {"content_hash": "img2", "score": 0.8},
        ])
        embedding_client = FakeEmbeddingClient()
        svc = SearchService(settings=Settings(jina_api_key="k"), repository=repo,
                            embedding_client=embedding_client, vector_index=vector_index)
        results = await svc.search_images("test", tag_ids=[1, 2])
        assert vector_index.last_content_hash_filter == {"img1", "img2"}

    @pytest.mark.anyio
    async def test_search_with_empty_tag_filter_returns_empty(self):
        """When tag filter matches no images, return [] without calling vector index."""
        repo = FakeRepository()
        repo.tag_filter_result = set()
        vector_index = FakeVectorIndex([])
        embedding_client = FakeEmbeddingClient()
        svc = SearchService(settings=Settings(jina_api_key="k"), repository=repo,
                            embedding_client=embedding_client, vector_index=vector_index)
        results = await svc.search_images("test", tag_ids=[1])
        assert results == []
        assert vector_index.last_content_hash_filter is None  # never called

    @pytest.mark.anyio
    async def test_search_with_tag_and_category_intersects(self):
        """When both tag_ids and category_id provided, intersection is used."""
        repo = FakeRepository()
        repo.tag_filter_result = {"img1", "img2"}
        repo.category_filter_result = {"img2", "img3"}
        repo.images = {"img2": build_image_record(content_hash="img2")}
        vector_index = FakeVectorIndex([{"content_hash": "img2", "score": 0.9}])
        embedding_client = FakeEmbeddingClient()
        svc = SearchService(settings=Settings(jina_api_key="k"), repository=repo,
                            embedding_client=embedding_client, vector_index=vector_index)
        results = await svc.search_images("test", tag_ids=[1], category_id=1)
        assert vector_index.last_content_hash_filter == {"img2"}

    @pytest.mark.anyio
    async def test_search_results_include_tags_and_categories(self):
        """SearchResult should have populated tags and categories from batch methods."""
        repo = FakeRepository()
        repo.images = {"img1": build_image_record(content_hash="img1")}
        from image_search_mcp.domain.models import Tag, Category
        from datetime import datetime, timezone
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        repo.tags_for_images = {"img1": [Tag(id=1, name="sunset", created_at=now)]}
        repo.categories_for_images = {"img1": [Category(id=1, name="Nature", parent_id=None, sort_order=0, created_at=now)]}
        vector_index = FakeVectorIndex([{"content_hash": "img1", "score": 0.9}])
        embedding_client = FakeEmbeddingClient()
        svc = SearchService(settings=Settings(jina_api_key="k"), repository=repo,
                            embedding_client=embedding_client, vector_index=vector_index)
        results = await svc.search_images("test")
        assert len(results) == 1
        assert len(results[0].tags) == 1
        assert results[0].tags[0].name == "sunset"
        assert len(results[0].categories) == 1
        assert results[0].categories[0].name == "Nature"

    @pytest.mark.anyio
    async def test_search_similar_with_tag_filter(self, tmp_path):
        """search_similar should also support tag filtering."""
        # Create a real image file for search_similar's path validation
        img_path = tmp_path / "query.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # minimal JPEG header

        repo = FakeRepository()
        repo.tag_filter_result = {"img2"}
        repo.images = {"img2": build_image_record(content_hash="img2")}
        vector_index = FakeVectorIndex([{"content_hash": "img2", "score": 0.85}])
        embedding_client = FakeEmbeddingClient()
        svc = SearchService(settings=Settings(jina_api_key="k", images_root=str(tmp_path)),
                            repository=repo, embedding_client=embedding_client,
                            vector_index=vector_index)
        results = await svc.search_similar(str(img_path), tag_ids=[1])
        assert vector_index.last_content_hash_filter == {"img2"}
```

Note: Adapt `FakeEmbeddingClient`, `FakeVectorIndex`, and test setup to match the exact patterns in the existing test file. The key tests above cover: filter passthrough, empty filter short-circuit, intersection, batch tag/category population, and search_similar with filters.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_search_service.py::TestSearchWithTagFilter -v`
Expected: FAIL

- [ ] **Step 3: Update SearchService.search_images() and search_similar()**

In `src/image_search_mcp/services/search.py`:

1. Add `tag_ids`, `category_id`, `include_subcategories` parameters to `search_images()` and `search_similar()`
2. Before calling `self._vector_index.search()`, compute the content_hash filter:

```python
content_hash_filter: set[str] | None = None
if tag_ids or category_id is not None:
    sets: list[set[str]] = []
    if tag_ids:
        sets.append(self._repository.filter_by_tags(tag_ids))
    if category_id is not None:
        sets.append(self._repository.filter_by_category(category_id, include_subcategories))
    content_hash_filter = sets[0]
    for s in sets[1:]:
        content_hash_filter &= s
    if not content_hash_filter:
        return []
```

3. Pass `content_hash_filter=content_hash_filter` to `self._vector_index.search()`
4. After `_resolve_results` builds the result list, populate tags/categories using batch methods:

```python
# After results are built:
if results:
    hashes = [r.content_hash for r in results]
    tags_map = self._repository.get_tags_for_images(hashes)
    cats_map = self._repository.get_categories_for_images(hashes)
    for r in results:
        r.tags = tags_map.get(r.content_hash, [])
        r.categories = cats_map.get(r.content_hash, [])
```

Apply this same pattern in both `search_images` and `search_similar`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_search_service.py -v`
Expected: All PASS (including existing tests — the new parameters have defaults)

- [ ] **Step 5: Commit**

```bash
git add src/image_search_mcp/services/search.py tests/unit/test_search_service.py
git commit -m "feat: add tag/category combination filtering to SearchService"
```

---

### Task 9: DI Wiring — RuntimeServices & App

**Files:**
- Modify: `src/image_search_mcp/runtime.py`
- Modify: `src/image_search_mcp/app.py`

- [ ] **Step 1: Add TagService to RuntimeServices**

In `src/image_search_mcp/runtime.py`:

1. Import `TagService`
2. Add `tag_service: TagService` field to `RuntimeServices` dataclass
3. In `build_runtime_services()`, construct `TagService(repository=repository)` and include it

- [ ] **Step 2: Run existing tests to verify nothing breaks**

Run: `pytest tests/ -v`
Expected: All existing tests pass. Some may need updating if they construct `RuntimeServices` directly — check `tests/integration/conftest.py` and update fixtures to pass `tag_service`.

- [ ] **Step 3: Commit**

```bash
git add src/image_search_mcp/runtime.py src/image_search_mcp/app.py
git commit -m "feat: wire TagService into RuntimeServices"
```

---

### Task 10: HTTP API — Tag & Category Routes

**Files:**
- Create: `src/image_search_mcp/web/tag_routes.py`
- Modify: `src/image_search_mcp/app.py`
- Test: `tests/integration/test_tag_api.py`

- [ ] **Step 1: Write integration tests for tag API**

Create `tests/integration/test_tag_api.py`.

**IMPORTANT:** Do NOT create the app via `create_app(settings=...)` directly — this starts real Milvus/Jina services. Instead, follow the existing integration test pattern: construct a `MetadataRepository` and `TagService` manually, create a minimal FastAPI app with only the tag router, and test against that. Alternatively, add a `tag_service` override parameter to `create_app()` following the existing pattern for `search_service`, `status_service`, and `job_runner`.

```python
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.services.tagging import TagService
from image_search_mcp.web.tag_routes import create_tag_router


@pytest.fixture
def app(tmp_path):
    """Create minimal app with only tag routes for testing."""
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    tag_service = TagService(repository=repo)
    app = FastAPI()
    app.include_router(create_tag_router(tag_service=tag_service))
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestTagAPI:
    @pytest.mark.anyio
    async def test_create_and_list_tags(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "sunset"

        resp = await client.get("/api/tags")
        assert resp.status_code == 200
        tags = resp.json()
        assert len(tags) == 1

    @pytest.mark.anyio
    async def test_rename_tag(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = resp.json()["id"]
        resp = await client.put(f"/api/tags/{tag_id}", json={"name": "sunrise"})
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_delete_tag(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = resp.json()["id"]
        resp = await client.delete(f"/api/tags/{tag_id}")
        assert resp.status_code == 204


class TestCategoryAPI:
    @pytest.mark.anyio
    async def test_create_and_get_tree(self, client):
        resp = await client.post("/api/categories", json={"name": "Nature"})
        assert resp.status_code == 201
        parent_id = resp.json()["id"]

        resp = await client.post("/api/categories", json={"name": "Flowers", "parent_id": parent_id})
        assert resp.status_code == 201

        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1

    @pytest.mark.anyio
    async def test_delete_category(self, client):
        resp = await client.post("/api/categories", json={"name": "Nature"})
        cat_id = resp.json()["id"]
        resp = await client.delete(f"/api/categories/{cat_id}")
        assert resp.status_code == 204

    @pytest.mark.anyio
    async def test_move_category_to_root(self, client):
        """move_to_root=true should reparent a child category to root."""
        resp = await client.post("/api/categories", json={"name": "Parent"})
        parent_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "Child", "parent_id": parent_id})
        child_id = resp.json()["id"]

        resp = await client.put(f"/api/categories/{child_id}", json={"move_to_root": True})
        assert resp.status_code == 200

        # Verify child is now a root category
        resp = await client.get("/api/categories")
        tree = resp.json()
        root_names = {n["name"] for n in tree}
        assert "Child" in root_names

    @pytest.mark.anyio
    async def test_move_category_to_new_parent(self, client):
        resp = await client.post("/api/categories", json={"name": "A"})
        a_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "B"})
        b_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "Child", "parent_id": a_id})
        child_id = resp.json()["id"]

        resp = await client.put(f"/api/categories/{child_id}", json={"move_to_parent_id": b_id})
        assert resp.status_code == 200

        resp = await client.get(f"/api/categories/{b_id}/children")
        children = resp.json()
        assert len(children) == 1
        assert children[0]["name"] == "Child"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/integration/test_tag_api.py -v`
Expected: FAIL — 404 (routes don't exist)

- [ ] **Step 3: Create tag_routes.py**

Create `src/image_search_mcp/web/tag_routes.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from image_search_mcp.services.tagging import TagService


# --- Request models ---

class CreateTagRequest(BaseModel):
    name: str

class RenameTagRequest(BaseModel):
    name: str

class CreateCategoryRequest(BaseModel):
    name: str
    parent_id: int | None = None

class UpdateCategoryRequest(BaseModel):
    name: str | None = None
    move_to_parent_id: int | None = None  # Explicit field: set to move; omit to keep current parent
    move_to_root: bool = False             # Set true to reparent to root (parent_id=None)

class AddTagToImageRequest(BaseModel):
    tag_id: int

class AddImageToCategoryRequest(BaseModel):
    category_id: int


def create_tag_router(*, tag_service: TagService) -> APIRouter:
    router = APIRouter()

    # --- Tags ---

    @router.post("/api/tags", status_code=201)
    def create_tag(body: CreateTagRequest):
        try:
            tag = tag_service.create_tag(body.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return tag.model_dump()

    @router.get("/api/tags")
    def list_tags():
        return [t.model_dump() for t in tag_service.list_tags()]

    @router.put("/api/tags/{tag_id}")
    def rename_tag(tag_id: int, body: RenameTagRequest):
        try:
            tag_service.rename_tag(tag_id, body.name)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    @router.delete("/api/tags/{tag_id}", status_code=204)
    def delete_tag(tag_id: int):
        tag_service.delete_tag(tag_id)

    # --- Categories ---

    @router.post("/api/categories", status_code=201)
    def create_category(body: CreateCategoryRequest):
        try:
            cat = tag_service.create_category(body.name, parent_id=body.parent_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return cat.model_dump()

    @router.get("/api/categories")
    def get_category_tree():
        tree = tag_service.get_category_tree()
        return [n.model_dump() for n in tree]

    @router.get("/api/categories/{category_id}/children")
    def get_category_children(category_id: int):
        children = tag_service.list_categories(parent_id=category_id)
        return [c.model_dump() for c in children]

    @router.put("/api/categories/{category_id}")
    def update_category(category_id: int, body: UpdateCategoryRequest):
        try:
            if body.name is not None:
                tag_service.rename_category(category_id, body.name)
            if body.move_to_root:
                tag_service.move_category(category_id, None)
            elif body.move_to_parent_id is not None:
                tag_service.move_category(category_id, body.move_to_parent_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True}

    @router.delete("/api/categories/{category_id}", status_code=204)
    def delete_category(category_id: int):
        tag_service.delete_category(category_id)

    # --- Image associations ---

    @router.post("/api/images/{content_hash}/tags", status_code=201)
    def add_tag_to_image(content_hash: str, body: AddTagToImageRequest):
        tag_service.add_tag_to_image(content_hash, body.tag_id)
        return {"ok": True}

    @router.delete("/api/images/{content_hash}/tags/{tag_id}", status_code=204)
    def remove_tag_from_image(content_hash: str, tag_id: int):
        tag_service.remove_tag_from_image(content_hash, tag_id)

    @router.get("/api/images/{content_hash}/tags")
    def get_image_tags(content_hash: str):
        return [t.model_dump() for t in tag_service.get_image_tags(content_hash)]

    @router.post("/api/images/{content_hash}/categories", status_code=201)
    def add_image_to_category(content_hash: str, body: AddImageToCategoryRequest):
        tag_service.add_image_to_category(content_hash, body.category_id)
        return {"ok": True}

    @router.delete("/api/images/{content_hash}/categories/{category_id}", status_code=204)
    def remove_image_from_category(content_hash: str, category_id: int):
        tag_service.remove_image_from_category(content_hash, category_id)

    @router.get("/api/images/{content_hash}/categories")
    def get_image_categories(content_hash: str):
        return [c.model_dump() for c in tag_service.get_image_categories(content_hash)]

    return router
```

- [ ] **Step 4: Register router in app.py**

In `src/image_search_mcp/app.py`:

1. Import `create_tag_router` from `web.tag_routes`
2. After the existing `include_router` call, add:

```python
app.include_router(create_tag_router(tag_service=services.tag_service))
```

- [ ] **Step 5: Run integration tests**

Run: `pytest tests/integration/test_tag_api.py -v`
Expected: All PASS

- [ ] **Step 6: Extend search endpoints with filter params**

Update the existing debug search endpoints in `src/image_search_mcp/web/routes.py`:

Add optional `tag_ids` and `category_id` fields to `DebugTextSearchRequest` and `DebugSimilarSearchRequest`, and pass them through to the service.

- [ ] **Step 7: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 8: Commit**

```bash
git add src/image_search_mcp/web/tag_routes.py src/image_search_mcp/app.py src/image_search_mcp/web/routes.py tests/integration/test_tag_api.py
git commit -m "feat: add HTTP API for tags, categories, and image associations"
```

---

### Task 11: Final Integration Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Start server locally and smoke test**

```bash
# In one terminal:
uvicorn image_search_mcp.app:create_app --factory --port 8000

# In another terminal:
curl -X POST http://localhost:8000/api/tags -H 'Content-Type: application/json' -d '{"name":"test-tag"}'
curl http://localhost:8000/api/tags
curl -X POST http://localhost:8000/api/categories -H 'Content-Type: application/json' -d '{"name":"Test Category"}'
curl http://localhost:8000/api/categories
```

- [ ] **Step 3: Commit any final fixes**

- [ ] **Step 4: Final commit message**

```bash
git log --oneline -10  # verify commit history looks clean
```
