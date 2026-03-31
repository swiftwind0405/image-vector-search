# Task 002: Search Tools — Implementation

**depends-on**: ["002-search-tools-test"]
**type**: impl
**files**:
- `src/image_search_mcp/tools/search_tools.py` (create)

## Description

Implement the two search tools that wrap `SearchService`.

### `tools/search_tools.py`
- Import `registry` from `.registry`
- Define `search_images` tool:
  - Parameters: `ctx: ToolContext, query: str, top_k: int = 5, min_score: float = 0.0, folder: str | None = None`
  - Validate folder path against `ctx.settings.images_root` if provided
  - Call `ctx.search_service.search_images(query=query, folder=folder, top_k=top_k, min_score=min_score)`
  - Return `{"results": [r.model_dump() for r in results]}`
- Define `search_similar` tool:
  - Parameters: `ctx: ToolContext, image_path: str, top_k: int = 5, min_score: float = 0.0, folder: str | None = None`
  - Call `ctx.search_service.search_similar(...)`
  - Return `{"results": [r.model_dump() for r in results]}`

## Verification

```bash
pytest tests/unit/test_search_tools.py -v
```

Expected: Both tests pass (Green phase).
