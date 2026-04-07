# Task 007: App Integration — Wire Registry into app.py

**depends-on**: ["002-search-tools-impl", "003-tag-tools-impl", "004-index-tools-impl", "005-mcp-adapter-impl", "006-http-adapter-impl"]
**type**: impl
**files**:
- `src/image_vector_search/tools/__init__.py` (modify — add tool module imports)
- `src/image_vector_search/app.py` (modify)
- `src/image_vector_search/mcp/server.py` (modify — delegate to mcp_adapter)

## Description

Wire everything together in the application factory.

### `tools/__init__.py`
- Add imports for all tool modules to trigger `@registry.tool` decorators:
  - `from . import search_tools, image_tools, tag_tools, index_tools`

### `app.py` changes
- Import `default_registry` from `image_vector_search.tools`
- Import `ToolContext` from `image_vector_search.tools.context`
- Import `build_mcp_from_registry` from `image_vector_search.adapters.mcp_adapter`
- Import `build_tool_router` from `image_vector_search.adapters.http_tool_adapter`
- After building runtime_services, create `ToolContext` from runtime services
- Replace `build_mcp_server(search_service)` with `build_mcp_from_registry(default_registry, tool_ctx)`
- Add `app.include_router(build_tool_router(default_registry, tool_ctx))`
- Keep all existing admin routes unchanged

### `mcp/server.py`
- Keep the file but make `build_mcp_server` delegate to `build_mcp_from_registry` for backwards compatibility (existing tests may reference it)
- Alternatively, update existing MCP tests to use the new adapter directly

## Verification

```bash
# Run all existing tests to ensure no regressions
pytest -v

# Manually verify the server starts
python -m image_vector_search &
# Test tool discovery
curl http://localhost:8000/api/tools
# Test tool invocation
curl -X POST http://localhost:8000/api/tools/get_index_status -H "Content-Type: application/json" -d '{}'
```

Expected: All existing tests pass. New endpoints respond correctly.
