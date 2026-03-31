# Task 001: Tool Registry Core — Implementation

**depends-on**: ["001-registry-core-test"]
**type**: impl
**files**:
- `src/image_search_mcp/tools/__init__.py` (create)
- `src/image_search_mcp/tools/registry.py` (create)
- `src/image_search_mcp/tools/context.py` (create)

## Description

Implement the core Tool Registry: `ToolDef` dataclass, `ToolRegistry` class with `@tool` decorator, `_schema_from_hints()` helper, and `ToolContext` dataclass.

### `tools/registry.py`
- Define `ToolDef` dataclass with fields: `name`, `description`, `fn`, `input_schema`
- Define `ToolRegistry` class with:
  - `tool(name, description)` decorator that registers functions and infers schema
  - `get_tools()` returns list of ToolDef
  - `get_tool(name)` returns ToolDef or None
- Implement `_schema_from_hints(fn)`:
  - Use `inspect.signature(fn)` to get parameters
  - Skip the first parameter if annotated as `ToolContext`
  - Use `pydantic.create_model()` to build a dynamic model from remaining params
  - Call `.model_json_schema()` on the model to get JSON Schema
  - Strip `title` keys from schema for cleanliness
- Create module-level singleton: `registry = ToolRegistry()`

### `tools/context.py`
- Define `ToolContext` frozen dataclass with fields: `search_service`, `tag_service`, `status_service`, `job_runner`, `settings`

### `tools/__init__.py`
- Re-export `ToolRegistry`, `ToolContext`, `registry as default_registry`
- Do NOT import tool modules yet (no tools defined yet)

## Verification

```bash
pytest tests/unit/test_registry.py -v
```

Expected: All 6 tests pass (Green phase).
