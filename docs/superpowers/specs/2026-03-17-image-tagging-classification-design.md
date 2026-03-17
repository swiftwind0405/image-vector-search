# Image Tagging & Classification Design

## Overview

Add manual tagging and hierarchical classification to the image vector search service. Users can organize images with free-form tags, predefined category labels, and tree-structured classification hierarchies. Tags and categories integrate with existing vector search as combination filters.

## Requirements

- **Free tags**: User-defined labels (e.g. "2024旅行", "待处理", "客户A"), many-to-many with images
- **Hierarchical categories**: Tree-structured classification (e.g. "工作 > 项目A > 设计稿"), many-to-many with images
- **Combination filtering**: Semantic search results can be filtered by tags and/or categories simultaneously
- **HTTP API only**: Exposed via REST endpoints; MCP tools unchanged
- **Manual only**: No AI-assisted auto-tagging in this iteration

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
| content_hash | TEXT    | NOT NULL, FK → images(content_hash) |
| tag_id       | INTEGER | FK → tags(id)                     |
| category_id  | INTEGER | FK → categories(id)               |
| created_at   | TEXT    | NOT NULL                          |

- `UNIQUE(content_hash, tag_id)` — no duplicate tag per image
- `UNIQUE(content_hash, category_id)` — no duplicate category per image
- `CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))` — exactly one of tag_id or category_id must be set

## Repository Layer

Extend `MetadataRepository` with new methods. All async, consistent with existing style.

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
- `delete_category(category_id)` — cascades to children and image_tags

### Image Association

- `add_tag_to_image(content_hash, tag_id)`
- `remove_tag_from_image(content_hash, tag_id)`
- `add_image_to_category(content_hash, category_id)`
- `remove_image_from_category(content_hash, category_id)`
- `get_image_tags(content_hash) → list[Tag]`
- `get_image_categories(content_hash) → list[Category]`

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

### Combination Filter Flow

1. If `tag_ids` or `category_id` specified, query repository for matching content_hash sets
2. If both specified, intersect the sets
3. If intersection is empty, return `[]` early
4. Pass content_hash set to `MilvusLiteIndex.search()` as an `in` filter on the `content_hash` field
5. Remaining logic (score threshold, folder filter, result assembly) unchanged

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
