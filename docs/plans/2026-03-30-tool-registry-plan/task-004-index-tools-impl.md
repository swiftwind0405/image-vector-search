# Task 004: Index & Image Tools — Implementation

**depends-on**: ["004-index-tools-test"]
**type**: impl
**files**:
- `src/image_search_mcp/tools/index_tools.py` (create)
- `src/image_search_mcp/tools/image_tools.py` (create)

## Description

### `tools/index_tools.py`
- **get_index_status** tool:
  - Parameters: `ctx: ToolContext`
  - Call `ctx.status_service.get_index_status()` and `ctx.status_service.list_recent_jobs(limit=5)`
  - Return `{"status": status.model_dump(), "recent_jobs": [j.model_dump() for j in jobs]}`

- **trigger_index** tool:
  - Parameters: `ctx: ToolContext, mode: Literal["incremental", "full_rebuild"]`
  - Call `ctx.job_runner.enqueue(mode)`
  - Return `{"job": job.model_dump()}`

### `tools/image_tools.py`
- **list_images** tool:
  - Parameters: `ctx: ToolContext, folder: str | None = None, tag_id: int | None = None, category_id: int | None = None`
  - Validate folder path if provided
  - Call `ctx.status_service.list_active_images_with_labels(folder=folder, tag_id=tag_id, category_id=category_id)`
  - Return `{"images": [img.model_dump() for img in images]}`

- **get_image_info** tool:
  - Parameters: `ctx: ToolContext, content_hash: str`
  - Call `ctx.status_service.get_image(content_hash)`, raise ValueError if None
  - Also fetch tags and categories for the image
  - Return combined dict with image record + tags + categories

## Verification

```bash
pytest tests/unit/test_index_tools.py -v
```

Expected: All index/image tool tests pass (Green phase).
