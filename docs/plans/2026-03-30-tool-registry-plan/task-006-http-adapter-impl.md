# Task 006: HTTP Tool Adapter — Implementation

**depends-on**: ["006-http-adapter-test"]
**type**: impl
**files**:
- `src/image_vector_search/adapters/http_tool_adapter.py` (create)

## Description

Implement `build_tool_router(registry, ctx)` that generates a FastAPI router for agent-facing HTTP tool invocation.

### `adapters/http_tool_adapter.py`
- Define `build_tool_router(registry: ToolRegistry, ctx: ToolContext) -> APIRouter`
- Create router with `prefix="/api/tools"`, `tags=["tools"]`
- **Discovery endpoint** `GET /api/tools`:
  - Return JSON array of `{"name", "description", "parameters"}` for each tool
  - Add `Cache-Control: public, max-age=3600` header
- **Invocation endpoint** `POST /api/tools/{tool_name}`:
  - Look up tool in registry, return 404 if not found
  - Parse request body as dict
  - Call `await tool_def.fn(ctx, **payload)`
  - Return result as JSON
  - Error mapping:
    - `ValueError` → 400
    - `FileNotFoundError` → 404
    - Other exceptions → 500 (log full traceback)

## Verification

```bash
pytest tests/unit/test_http_adapter.py -v
```

Expected: All HTTP adapter tests pass (Green phase).
