# Image Tagging & Classification Design

## Overview

Add manual tagging and hierarchical classification to the image vector search service. Users can organize images with free-form tags, predefined category labels, and tree-structured classification hierarchies. Tags and categories integrate with existing vector search as combination filters.

## Requirements

- **Free tags**: User-defined labels (e.g. "2024旅行", "待处理", "客户A"), many-to-many with images
- **Hierarchical categories**: Tree-structured classification (e.g. "工作 > 项目A > 设计稿"), many-to-many with images
- **Combination filtering**: Semantic search results can be filtered by tags and/or categories simultaneously
- **HTTP API only**: Exposed via REST endpoints; MCP tools unchanged
- **Manual only**: No AI-assisted auto-tagging in this iteration

## Domain Models

New Pydantic models in `domain/models.py`:

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
    children: list[CategoryNode] = []
```

## Data Model

Three new SQLite tables in `MetadataRepository`:

### `tags`

| Column     | Type    | Constraints            |
|------------|---------|------------------------|
| id         | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name       | TEXT    | NOT NULL UNIQUE        |
| created_at | TEXT    | NOT NULL               |

### `categories`

Adjacency-list model for tree structure.

| Column     | Type    | Constraints                        |
|------------|---------|------------------------------------|
| id         | INTEGER | PRIMARY KEY AUTOINCREMENT          |
| name       | TEXT    | NOT NULL                           |
| parent_id  | INTEGER | FK → categories(id), NULL = root   |
| sort_order | INTEGER | NOT NULL DEFAULT 0                 |
| created_at | TEXT    | NOT NULL                           |

- `UNIQUE(parent_id, name)` — no duplicate names under the same parent

### `image_tags`

Single join table for both tag and category associations.

| Column       | Type    | Constraints                       |
|--------------|---------|-----------------------------------|
| id           | INTEGER | PRIMARY KEY AUTOINCREMENT         |
| content_hash | TEXT    | NOT NULL, FK → images(content_hash) ON DELETE CASCADE |
| tag_id       | INTEGER | FK → tags(id) ON DELETE CASCADE   |
| category_id  | INTEGER | FK → categories(id) ON DELETE CASCADE |
| created_at   | TEXT    | NOT NULL                          |

- `UNIQUE(content_hash, tag_id)` — no duplicate tag per image
- `UNIQUE(content_hash, category_id)` — no duplicate category per image
- `CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))` — exactly one of tag_id or category_id must be set

Indexes:
- `CREATE INDEX idx_image_tags_content_hash ON image_tags(content_hash)`
- `CREATE INDEX idx_image_tags_tag_id ON image_tags(tag_id)`
- `CREATE INDEX idx_image_tags_category_id ON image_tags(category_id)`

## Repository Layer

Extend `MetadataRepository` with new methods. All synchronous `def`, consistent with existing repository style.

### Tag CRUD

- `create_tag(name) → Tag`
- `list_tags() → list[Tag]`
- `rename_tag(tag_id, new_name)`
- `delete_tag(tag_id)` — cascades to image_tags

### Category CRUD

- `create_category(name, parent_id=None) → Category`
- `list_categories(parent_id=None) → list[Category]` — children of a given parent
- `get_category_tree() → list[CategoryNode]` — full tree
- `rename_category(category_id, new_name)`
- `move_category(category_id, new_parent_id)` — reparent
- `delete_category(category_id)` — uses recursive CTE to find all descendant IDs, deletes their image_tags rows, then deletes the categories, all in a single transaction

### Image Association

- `add_tag_to_image(content_hash, tag_id)`
- `remove_tag_from_image(content_hash, tag_id)`
- `add_image_to_category(content_hash, category_id)`
- `remove_image_from_category(content_hash, category_id)`
- `get_image_tags(content_hash) → list[Tag]`
- `get_image_categories(content_hash) → list[Category]`
- `get_tags_for_images(content_hashes: list[str]) → dict[str, list[Tag]]` — batch query to avoid N+1
- `get_categories_for_images(content_hashes: list[str]) → dict[str, list[Category]]` — batch query to avoid N+1

### Filter Queries (for SearchService)

- `filter_by_tags(tag_ids) → set[str]` — content_hashes having ALL specified tags
- `filter_by_category(category_id, include_subcategories=True) → set[str]` — content_hashes in category (and descendants if requested)

## Service Layer

### New: `TagService` (`services/tagging.py`)

Thin business-logic layer over repository methods. Responsibilities:

- Input validation (non-empty names, no circular category references)
- Delegates to `MetadataRepository`

### Extended: `SearchService`

Add optional filter parameters to existing search methods:

```python
async def search_images(
    self, query: str, top_k: int = 5, min_score: float = 0.0,
    folder: str | None = None,
    tag_ids: list[int] | None = None,
    category_id: int | None = None,
    include_subcategories: bool = True,
) -> list[SearchResult]:
```

Same extension for `search_similar`.

### VectorIndex Changes

The `VectorIndex` abstract base class and `MilvusLiteIndex` need a new optional parameter:

```python
# VectorIndex (abstract)
def search(self, vector: list[float], limit: int, embedding_key: str,
           content_hash_filter: set[str] | None = None) -> list[dict]:

# MilvusLiteIndex implementation
# When content_hash_filter is provided, build a Milvus `in` filter expression:
#   f"content_hash in {list(content_hash_filter)}"
# Combined with existing embedding_key filter via `and`.
```

### Combination Filter Flow

1. If `tag_ids` or `category_id` specified, query repository for matching content_hash sets
2. If both specified, intersect the sets
3. If intersection is empty, return `[]` early
4. Pass content_hash set to `MilvusLiteIndex.search()` via the new `content_hash_filter` parameter
5. Remaining logic (score threshold, folder filter, result assembly) unchanged
6. Use batch methods (`get_tags_for_images`, `get_categories_for_images`) to populate tags/categories on SearchResult

### Extended: `SearchResult`

```python
class SearchResult:
    content_hash: str
    path: str
    score: float
    width: int
    height: int
    mime_type: str
    tags: list[Tag] = []
    categories: list[Category] = []
```

## HTTP API

### Dependency Injection Wiring

- Add `TagService` to the `RuntimeServices` dataclass in `runtime.py`
- Construct it in `build_runtime_services()` (depends on `MetadataRepository`)
- Create `create_tag_router(tag_service: TagService) → APIRouter` in a new `web/tag_routes.py`
- Include the router in `app.py` during app construction, same pattern as existing web router

### Routes

New route groups registered in `app.py`.

### Tags — `/api/tags`

| Method | Path             | Body / Params  | Description      |
|--------|------------------|----------------|------------------|
| POST   | `/api/tags`      | `{name}`       | Create tag       |
| GET    | `/api/tags`      | —              | List all tags    |
| PUT    | `/api/tags/{id}` | `{name}`       | Rename tag       |
| DELETE | `/api/tags/{id}` | —              | Delete tag       |

### Categories — `/api/categories`

| Method | Path                            | Body / Params         | Description               |
|--------|---------------------------------|-----------------------|---------------------------|
| POST   | `/api/categories`               | `{name, parent_id?}`  | Create category           |
| GET    | `/api/categories`               | —                     | Get full category tree    |
| GET    | `/api/categories/{id}/children` | —                     | Get direct children       |
| PUT    | `/api/categories/{id}`          | `{name?, parent_id?}` | Rename or move category   |
| DELETE | `/api/categories/{id}`          | —                     | Delete category + children |

### Image Associations — `/api/images/{content_hash}/...`

| Method | Path                                            | Body / Params  | Description           |
|--------|-------------------------------------------------|----------------|-----------------------|
| POST   | `/api/images/{content_hash}/tags`               | `{tag_id}`     | Add tag to image      |
| DELETE | `/api/images/{content_hash}/tags/{tag_id}`      | —              | Remove tag from image |
| GET    | `/api/images/{content_hash}/tags`               | —              | Get image's tags      |
| POST   | `/api/images/{content_hash}/categories`         | `{category_id}` | Add image to category |
| DELETE | `/api/images/{content_hash}/categories/{cat_id}` | —            | Remove from category  |
| GET    | `/api/images/{content_hash}/categories`         | —              | Get image's categories|

### Search Extension

Existing search endpoints gain optional query parameters: `tag_ids`, `category_id`, `include_subcategories`.

## What's NOT in Scope

- MCP tool changes (tags are HTTP API / Admin UI only)
- Admin UI for tag/category management (separate future work)
- AI-assisted auto-tagging
- Batch tag operations
