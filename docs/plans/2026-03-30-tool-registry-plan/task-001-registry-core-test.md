# Task 001: Tool Registry Core — Tests

**depends-on**: []
**type**: test
**files**:
- `tests/unit/test_registry.py` (create)

## BDD Scenarios

```gherkin
Scenario: Register a tool via decorator
  Given an empty ToolRegistry
  When I decorate an async function with @registry.tool(name="my_tool", description="Does things")
  Then the registry contains a tool named "my_tool"
  And the tool's description is "Does things"
  And the tool's handler is the decorated function

Scenario: Infer input schema from type hints
  Given a function with parameters (query: str, top_k: int = 5, folder: str | None = None)
  When I register it as a tool
  Then the input schema has "query" as a required string property
  And "top_k" as an optional integer property with default 5
  And "folder" as an optional nullable string property

Scenario: Infer schema for Literal action parameter
  Given a function with parameter action: Literal["create", "delete", "list"]
  When I register it as a tool
  Then the input schema has "action" as a required string with enum ["create", "delete", "list"]

Scenario: Exclude ToolContext from schema
  Given a function with first parameter ctx: ToolContext
  When I register it as a tool
  Then the input schema does not contain a "ctx" property
  And the schema only includes user-facing parameters

Scenario: List all registered tools
  Given a registry with tools "search_images", "manage_tags", "get_index_status"
  When I call registry.get_tools()
  Then I receive 3 ToolDef objects
  And each has name, description, fn, and input_schema fields

Scenario: Get tool by name
  Given a registry with a tool named "search_images"
  When I call registry.get_tool("search_images")
  Then I receive the ToolDef for "search_images"
  When I call registry.get_tool("nonexistent")
  Then I receive None
```

## Steps

1. Create `tests/unit/test_registry.py`
2. Write a test for each scenario above:
   - `test_register_tool_via_decorator` — create a ToolRegistry, decorate a dummy async function, assert name/description/handler are stored
   - `test_infer_schema_from_type_hints` — register a function with `(ctx: ToolContext, query: str, top_k: int = 5, folder: str | None = None)`, assert input_schema has correct properties, required fields, defaults
   - `test_infer_literal_enum_schema` — register a function with `action: Literal["create", "delete", "list"]`, assert enum constraint in schema
   - `test_exclude_tool_context_from_schema` — register a function with `ctx: ToolContext` as first param, assert "ctx" not in schema properties
   - `test_list_all_tools` — register 3 tools, call `get_tools()`, assert 3 ToolDef objects with correct fields
   - `test_get_tool_by_name` — register a tool, assert `get_tool("name")` returns it, `get_tool("missing")` returns None
3. All tests should import from `image_search_mcp.tools.registry` (which does not exist yet — tests will fail)

## Verification

```bash
pytest tests/unit/test_registry.py -v
```

Expected: All tests fail with ImportError (Red phase — `tools/registry.py` does not exist yet).
