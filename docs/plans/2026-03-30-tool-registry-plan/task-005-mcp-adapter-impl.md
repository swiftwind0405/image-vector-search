# Task 005: MCP Adapter — Implementation

**depends-on**: ["005-mcp-adapter-test"]
**type**: impl
**files**:
- `src/image_vector_search/adapters/mcp_adapter.py` (create)

## Description

Implement `build_mcp_from_registry(registry, ctx)` that generates a FastMCP server from the tool registry.

### `adapters/mcp_adapter.py`
- Define `build_mcp_from_registry(registry: ToolRegistry, ctx: ToolContext) -> FastMCP`
- For each ToolDef in registry:
  - Create a wrapper async function that:
    1. Calls `tool_def.fn(ctx, **kwargs)`
    2. Converts result dict to structured content
  - Set `__name__`, `__qualname__`, `__doc__`, `__signature__`, `__annotations__` on wrapper
    - Strip `ctx` parameter from signature (use `inspect.signature` to rebuild without first param)
    - Copy type annotations without `ctx`
  - Use closure factory `_make_handler(td=tool_def)` to avoid late-binding in loop
  - Call `mcp.add_tool(Tool.from_function(wrapper, name=td.name, description=td.description))`
- Return the FastMCP instance

Key implementation detail: FastMCP's `Tool.from_function()` reads `__signature__` to infer parameter schema. The wrapper MUST have a correct `__signature__` without the `ctx` parameter.

## Verification

```bash
pytest tests/unit/test_mcp_adapter.py -v
```

Expected: All MCP adapter tests pass (Green phase).
