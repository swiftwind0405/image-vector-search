# Tool Registry Hybrid Architecture Design

## Context

The image-vector-search project exposes image search capabilities via MCP (2 tools) and HTTP REST API (30+ endpoints). The current architecture has these problems:

1. **MCP tools are too few** — only `search_images` and `search_similar`, while the HTTP API exposes tags, categories, indexing, bulk operations
2. **Dual maintenance** — MCP tools in `mcp/server.py` and HTTP routes in `web/*_routes.py` duplicate the same service calls with different boilerplate
3. **No agent discoverability** — agents can't discover available capabilities programmatically
4. **Protocol lock-in** — adding a new protocol (OpenClaw HTTP, A2A) requires rewriting all tool definitions

## Requirements

1. **Single source of truth** — Define each tool once, generate all protocol bindings automatically
2. **Task-oriented tools** — ~8-10 tools grouped by intent (not 30+ CRUD endpoints)
3. **Decorator-based registration** — `@registry.tool` with schema inferred from type hints
4. **Auto-generate adapters** — MCP adapter and HTTP adapter from the same registry
5. **OpenClaw integration** — HTTP API endpoint (`POST /api/tools/{name}`) + tool discovery (`GET /api/tools`)
6. **Preserve existing behavior** — MCP endpoint at `/mcp` continues to work; existing HTTP admin routes unchanged

## Rationale

**Why a Tool Registry instead of just expanding MCP tools?**

MCP is one protocol among many. OpenClaw prefers HTTP API direct calls. Future agents may use A2A or OpenAPI function calling. A registry abstracts the tool definition from the protocol, enabling multi-protocol support with zero duplication.

**Why task-oriented granularity?**

Agents think in tasks ("tag these images"), not CRUD operations ("POST tag, then POST image-tag association"). Fewer, higher-level tools reduce agent cognitive load and token usage. An `action` parameter within a tool (e.g., `manage_tags(action="create", name="landscape")`) maps naturally to how agents reason.

**Why decorator style?**

Matches the existing FastMCP `@mcp.tool` pattern the codebase already uses. Type hints → JSON Schema is proven (FastMCP uses Pydantic TypeAdapter internally). Minimal learning curve.

## Detailed Design

### Component Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Consumers                          │
│  MCP Client  │  OpenClaw Agent  │  HTTP Client      │
└──────┬───────┴────────┬─────────┴────────┬──────────┘
       │                │                  │
       ▼                ▼                  ▼
┌──────────┐  ┌─────────────────┐  ┌──────────────┐
│ /mcp     │  │ POST /api/tools │  │ /api/* (admin│
│ (FastMCP)│  │ GET /api/tools  │  │   routes)    │
└──────┬───┘  └────────┬────────┘  └──────────────┘
       │               │               (unchanged)
       ▼               ▼
┌──────────────────────────────┐
│      Protocol Adapters       │
│  mcp_adapter │  http_adapter │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        Tool Registry         │
│  @registry.tool decorators   │
│  ToolDef: name, desc, schema │
│  handler: async fn(ctx, ...) │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│        ToolContext            │
│  search_service, tag_service │
│  status_service, job_runner  │
│  settings                    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│     Services (unchanged)     │
│  SearchService, TagService   │
│  StatusService, JobRunner    │
└──────────────────────────────┘
```

### New File Layout

```
src/image_search_mcp/
├── tools/                          # NEW: Tool Registry
│   ├── __init__.py                 # exports registry, ToolContext
│   ├── registry.py                 # ToolRegistry class, @tool decorator, ToolDef
│   ├── context.py                  # ToolContext dataclass
│   ├── search_tools.py             # search_images, search_similar
│   ├── image_tools.py              # list_images, get_image_info
│   ├── tag_tools.py                # manage_tags, manage_categories, tag_images
│   └── index_tools.py              # get_index_status, trigger_index
├── adapters/
│   ├── mcp_adapter.py              # NEW: registry → FastMCP server
│   └── http_tool_adapter.py        # NEW: registry → FastAPI router
├── mcp/
│   └── server.py                   # REPLACED: now delegates to mcp_adapter
└── ...
```

### Core Types

#### ToolRegistry (`tools/registry.py`)

The registry instance (singleton) lives in `registry.py` to avoid circular imports. Tool modules import it directly from there.

```python
@dataclass
class ToolDef:
    name: str
    description: str
    fn: Callable                # async fn(ctx: ToolContext, **params)
    input_schema: dict          # JSON Schema from type hints (informational, for discovery)

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable:
        """Decorator to register a tool."""
        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            tool_desc = description or fn.__doc__ or ""
            input_schema = _schema_from_hints(fn)   # Pydantic TypeAdapter, excludes ctx
            self._tools[tool_name] = ToolDef(
                name=tool_name,
                description=tool_desc,
                fn=fn,
                input_schema=input_schema,
            )
            return fn
        return decorator

    def get_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

# Module-level singleton — tool modules import this directly
registry = ToolRegistry()
```

Tool names: snake_case, alphanumeric + underscore only, unique across registry.

Schema extraction uses `inspect.signature()` + Pydantic `TypeAdapter` to convert type hints to JSON Schema, following the same approach FastMCP uses internally.

#### ToolContext (`tools/context.py`)

```python
@dataclass(slots=True)
class ToolContext:
    search_service: SearchService
    tag_service: TagService
    status_service: StatusService
    job_runner: JobRunner
    settings: Settings
```

Built from `RuntimeServices` in `runtime.py`. Passed as first argument to every tool handler.

### Tool Definitions (~9 tools)

| Tool | Description | Service Methods Used |
|------|-------------|---------------------|
| `search_images` | Text-based semantic search | `SearchService.search_images` |
| `search_similar` | Find visually similar images | `SearchService.search_similar` |
| `list_images` | List/filter active images | `StatusService.list_active_images_with_labels` |
| `get_image_info` | Get single image details | `StatusService.get_image` + tag/category lookups |
| `manage_tags` | Create/rename/delete/list tags | `TagService.create_tag/rename_tag/delete_tag/list_tags` |
| `manage_categories` | Create/rename/delete/move/list categories | `TagService.*_category` methods |
| `tag_images` | Add/remove tags and categories from images | `TagService.add_tag_to_image/remove_tag_from_image/add_image_to_category/remove_image_from_category` |
| `get_index_status` | Get indexing stats and recent jobs | `StatusService.get_index_status` + `list_recent_jobs` |
| `trigger_index` | Start incremental or full rebuild | `JobRunner.enqueue` |

#### Example Tool Definition

```python
# tools/tag_tools.py
from typing import Literal
from tools import registry, ToolContext
from domain.models import Tag, Category, CategoryNode

@registry.tool(
    name="manage_tags",
    description="Create, rename, delete, or list image tags.",
)
async def manage_tags(
    ctx: ToolContext,
    action: Literal["create", "rename", "delete", "list"],
    name: str | None = None,
    tag_id: int | None = None,
    new_name: str | None = None,
) -> dict:
    if action == "create":
        tag = ctx.tag_service.create_tag(name)
        return {"tag": tag.model_dump()}
    elif action == "rename":
        ctx.tag_service.rename_tag(tag_id, new_name)
        return {"ok": True}
    elif action == "delete":
        ctx.tag_service.delete_tag(tag_id)
        return {"ok": True}
    elif action == "list":
        tags = ctx.tag_service.list_tags()
        return {"tags": [t.model_dump() for t in tags]}
```

### Adapter: MCP (`adapters/mcp_adapter.py`)

```python
def build_mcp_from_registry(registry: ToolRegistry, ctx: ToolContext) -> FastMCP:
    mcp = FastMCP("image-search-mcp")

    for tool_def in registry.get_tools():
        # Create closure that binds ctx and tool_def.fn
        async def make_handler(td=tool_def):
            async def handler(**kwargs):
                result = await td.fn(ctx, **kwargs)
                return _to_tool_result(result)
            handler.__name__ = td.name
            handler.__doc__ = td.description
            # Copy type annotations from original fn (minus ctx param)
            handler.__annotations__ = _strip_ctx_annotations(td.fn)
            return handler

        fn = asyncio.run(make_handler())  # or sync closure
        mcp.add_tool(Tool.from_function(fn, name=tool_def.name, description=tool_def.description))

    return mcp
```

Key: FastMCP's `Tool.from_function()` extracts the JSON Schema from the wrapper function's type hints. We copy annotations from the original tool function (minus the `ctx` parameter) so FastMCP sees the correct schema.

### Adapter: HTTP (`adapters/http_tool_adapter.py`)

```python
def build_tool_router(registry: ToolRegistry, ctx: ToolContext) -> APIRouter:
    router = APIRouter(prefix="/api/tools", tags=["tools"])

    @router.get("")
    async def list_tools():
        """Tool discovery endpoint for OpenClaw and other agents."""
        return [
            {
                "name": td.name,
                "description": td.description,
                "parameters": td.input_schema,
            }
            for td in registry.get_tools()
        ]

    @router.post("/{tool_name}")
    async def invoke_tool(tool_name: str, payload: dict = Body(...)):
        td = registry.get_tool(tool_name)
        if td is None:
            raise HTTPException(404, f"Tool '{tool_name}' not found")
        try:
            result = await td.fn(ctx, **payload)
            return result
        except ValueError as e:
            raise HTTPException(400, str(e))
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))

    return router
```

### OpenClaw Skill Integration

Create a skill package at project root:

```
openclaw-skill/
├── SKILL.md
└── README.md
```

**SKILL.md:**
```yaml
---
name: image-search
description: Search and manage a local image library using vector embeddings. Find images by text description, visual similarity, and organize with tags and categories.
user-invocable: true
metadata: {"openclaw": {"primaryEnv": "IMAGE_SEARCH_URL"}}
---

## Configuration

Set the `IMAGE_SEARCH_URL` environment variable to the server URL (e.g., `http://localhost:8000`).

## Available Tools

Discover all tools: `GET $IMAGE_SEARCH_URL/api/tools`

## Usage Examples

### Search images by text
```bash
curl -X POST $IMAGE_SEARCH_URL/api/tools/search_images \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over mountains", "top_k": 5}'
```

### Tag images
```bash
curl -X POST $IMAGE_SEARCH_URL/api/tools/manage_tags \
  -H "Content-Type: application/json" \
  -d '{"action": "create", "name": "landscape"}'
```

### Check index status
```bash
curl -X POST $IMAGE_SEARCH_URL/api/tools/get_index_status \
  -H "Content-Type: application/json" \
  -d '{}'
```
```

### Integration into app.py

Minimal changes to `app.py`:

```python
# In create_app():
from image_search_mcp.tools import default_registry
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.adapters.mcp_adapter import build_mcp_from_registry
from image_search_mcp.adapters.http_tool_adapter import build_tool_router

# Build context from runtime services
tool_ctx = ToolContext(
    search_service=search_service,
    tag_service=runtime_services.tag_service,
    status_service=status_service,
    job_runner=job_runner,
    settings=app_settings,
)

# MCP from registry (replaces build_mcp_server)
mcp_server = build_mcp_from_registry(default_registry, tool_ctx)
app.mount("/mcp", mcp_server.http_app(path="/"))

# HTTP tool endpoint for OpenClaw
app.include_router(build_tool_router(default_registry, tool_ctx))
```

### Migration Strategy

1. Existing admin HTTP routes (`/api/images`, `/api/tags`, etc.) remain unchanged — they serve the admin UI
2. New `/api/tools/*` routes serve agents (OpenClaw, etc.)
3. MCP endpoint `/mcp` is regenerated from registry instead of hand-written
4. Old `mcp/server.py` is replaced by `adapters/mcp_adapter.py`

## Design Documents

- [BDD Specifications](./bdd-specs.md) - Behavior scenarios and testing strategy
- [Architecture](./architecture.md) - System architecture and component details
- [Best Practices](./best-practices.md) - Security, performance, and code quality guidelines
