# Architecture Details

## Schema Extraction Mechanism

The Tool Registry reuses the same approach FastMCP uses internally:

1. `inspect.signature(fn)` extracts parameter names, types, defaults
2. The `ctx: ToolContext` parameter is excluded (dependency injection, not user input)
3. Remaining parameters are wrapped in a dynamically created Pydantic `BaseModel` via `pydantic.create_model()`
4. `TypeAdapter(model).json_schema()` generates the JSON Schema
5. Schema is compressed (remove titles, resolve `$ref`) for cleaner output

### Type Mapping

| Python Type | JSON Schema |
|---|---|
| `str` | `{"type": "string"}` |
| `int` | `{"type": "integer"}` |
| `float` | `{"type": "number"}` |
| `bool` | `{"type": "boolean"}` |
| `str \| None` | `{"type": ["string", "null"]}` |
| `Literal["a", "b"]` | `{"type": "string", "enum": ["a", "b"]}` |
| `list[str]` | `{"type": "array", "items": {"type": "string"}}` |

### Action Parameter Pattern

Task-oriented tools use `action: Literal[...]` to multiplex operations:

```python
@registry.tool
async def manage_tags(
    ctx: ToolContext,
    action: Literal["create", "rename", "delete", "list"],
    name: str | None = None,       # required for "create"
    tag_id: int | None = None,     # required for "rename", "delete"
    new_name: str | None = None,   # required for "rename"
) -> dict: ...
```

The JSON Schema shows all parameters as optional (except `action`). The tool handler validates required combinations at runtime and raises `ValueError` with a clear message.

## Adapter Architecture

### MCP Adapter

The MCP adapter must bridge between the registry's `fn(ctx, **params)` calling convention and FastMCP's expected function signature.

**Approach: Dynamic function generation with `makefun`-style signature rewriting**

For each registered tool, create a wrapper function that:
1. Has the same parameter signature as the original (minus `ctx`)
2. Closures over `ctx` and the original handler
3. Has correct `__name__`, `__doc__`, `__annotations__`, and `__signature__`

```python
import inspect

def build_mcp_from_registry(registry: ToolRegistry, ctx: ToolContext) -> FastMCP:
    mcp = FastMCP("image-search-mcp")

    for tool_def in registry.get_tools():
        # Strip ctx from signature and annotations
        orig_sig = inspect.signature(tool_def.fn)
        new_params = [
            p for name, p in orig_sig.parameters.items() if name != "ctx"
        ]
        new_sig = orig_sig.replace(parameters=new_params)
        new_annotations = {
            name: p.annotation
            for name, p in orig_sig.parameters.items()
            if name != "ctx" and p.annotation is not inspect.Parameter.empty
        }
        if "return" in tool_def.fn.__annotations__:
            new_annotations["return"] = tool_def.fn.__annotations__["return"]

        # Closure to bind tool_def
        def _make_handler(td=tool_def):
            async def handler(**kwargs):
                return await td.fn(ctx, **kwargs)
            handler.__name__ = td.name
            handler.__qualname__ = td.name
            handler.__doc__ = td.description
            handler.__signature__ = new_sig
            handler.__annotations__ = new_annotations
            return handler

        wrapper = _make_handler()
        mcp.add_tool(Tool.from_function(wrapper, name=tool_def.name, description=tool_def.description))

    return mcp
```

Key: `__signature__` is set explicitly so FastMCP's `Tool.from_function()` sees the correct parameters without `ctx`. The closure factory `_make_handler(td=tool_def)` avoids late-binding bugs in loops.

**Why `Tool.from_function()` instead of passing pre-computed schemas?**

FastMCP's `Tool` constructor accepts `parameters` (dict) directly, but `Tool.from_function()` is the documented, tested path. Using it ensures compatibility with FastMCP's schema compression, `$ref` resolution, and future changes.

### HTTP Tool Adapter

The HTTP adapter is simpler — it receives raw JSON and passes it to the tool handler:

```
POST /api/tools/search_images
Content-Type: application/json
{"query": "sunset", "top_k": 5}
```

**Validation strategy:**
- Input validation delegated to the tool handler (same as MCP path)
- Additional schema-based validation via `jsonschema.validate()` is optional but recommended for the HTTP path since it lacks MCP's built-in validation

**Discovery endpoint:**

```
GET /api/tools
→ [
    {"name": "search_images", "description": "...", "parameters": {...}},
    {"name": "manage_tags", "description": "...", "parameters": {...}},
    ...
  ]
```

This is the endpoint OpenClaw skills reference to discover available capabilities.

## ToolContext Lifecycle

```
create_app()
  → build_runtime_services(settings)
    → RuntimeServices (all services wired)
  → ToolContext(
      search_service=runtime_services.search_service,
      tag_service=runtime_services.tag_service,
      status_service=runtime_services.status_service,
      job_runner=runtime_services.job_runner,
      settings=app_settings,
    )
  → build_mcp_from_registry(registry, ctx)
  → build_tool_router(registry, ctx)
```

ToolContext is created once at app startup and shared across all tool invocations. It is immutable (frozen dataclass). Services within it hold shared references to adapters (embedding client, vector index) but are safe for concurrent async use — no request-scoped mutable state.

## Path Validation Boundary

Tools that accept file paths (`folder`, `image_path`) validate at the tool handler level:

```python
def _validate_folder(folder: str | None, images_root: Path) -> str | None:
    if folder is None:
        return None
    resolved = (images_root / folder).resolve()
    if not resolved.is_relative_to(images_root.resolve()):
        raise ValueError(f"Folder path escapes images root: {folder}")
    return folder
```

Services receive pre-validated relative paths. This is the first validation boundary (services may have their own checks as defense in depth).

## Tool Registration Order

To avoid circular imports, the registry instance lives in `registry.py` (not `__init__.py`). Tool modules import `registry` from there. `__init__.py` re-exports everything.

```python
# tools/registry.py
class ToolRegistry:
    ...

# Module-level singleton
registry = ToolRegistry()
```

```python
# tools/search_tools.py
from .registry import registry  # No circular import — registry.py has no tool imports

@registry.tool(name="search_images", ...)
async def search_images(ctx: ToolContext, query: str, ...) -> dict:
    ...
```

```python
# tools/__init__.py
from .registry import ToolRegistry, registry as default_registry
from .context import ToolContext

# Import tool modules to trigger @registry.tool decorators
from . import search_tools  # noqa: F401
from . import image_tools   # noqa: F401
from . import tag_tools     # noqa: F401
from . import index_tools   # noqa: F401
```

Import chain: `tools/__init__.py` → `tools/registry.py` (creates singleton) → then `tools/search_tools.py` → `tools/registry.py` (already imported, gets singleton). No circular dependency.

## Error Handling

Tools raise standard Python exceptions. Adapters translate them:

| Exception | MCP Behavior | HTTP Status |
|---|---|---|
| `ValueError` | `isError=True`, message in content | 400 Bad Request |
| `FileNotFoundError` | `isError=True`, message in content | 404 Not Found |
| `PermissionError` | `isError=True`, message in content | 403 Forbidden |
| Other | `isError=True`, generic message | 500 Internal Server Error |

Both adapters log the full exception for debugging.

## Relationship to Existing HTTP Routes

The existing admin routes (`/api/images`, `/api/tags`, `/api/jobs`, etc.) are **not replaced**. They continue to serve the admin web UI with their current request/response formats.

The new `/api/tools/*` routes serve a different purpose: agent-facing tool invocation with consistent input/output conventions. Both route sets call the same underlying services.

Over time, the admin UI could migrate to use `/api/tools/*`, but this is not in scope for this design.
