# Task 003: Tag & Category Tools — Implementation

**depends-on**: ["003-tag-tools-test"]
**type**: impl
**files**:
- `src/image_search_mcp/tools/tag_tools.py` (create)

## Description

Implement three task-oriented tools that wrap TagService methods.

### `tools/tag_tools.py`
- Import `registry` from `.registry`

- **manage_tags** tool:
  - Parameters: `ctx, action: Literal["create", "rename", "delete", "list"], name: str | None, tag_id: int | None, new_name: str | None`
  - Validate required param combinations per action (raise ValueError if missing)
  - Dispatch to appropriate TagService method
  - Return structured dict response

- **manage_categories** tool:
  - Parameters: `ctx, action: Literal["create", "rename", "delete", "move", "list"], name: str | None, category_id: int | None, new_name: str | None, parent_id: int | None`
  - Similar dispatch pattern to manage_tags
  - "list" action returns category tree via `get_category_tree()`
  - "move" action calls `move_category(category_id, parent_id)` (None parent_id = move to root)

- **tag_images** tool:
  - Parameters: `ctx, action: Literal["add_tag", "remove_tag", "add_category", "remove_category", "list_tags", "list_categories"], content_hash: str, tag_id: int | None, category_id: int | None`
  - Dispatch to corresponding TagService association methods

## Verification

```bash
pytest tests/unit/test_tag_tools.py -v
```

Expected: All tag/category tool tests pass (Green phase).
