# Task 005: MCP Adapter — Tests

**depends-on**: ["001-registry-core-impl"]
**type**: test
**files**:
- `tests/unit/test_mcp_adapter.py` (create)

## BDD Scenarios

```gherkin
Scenario: Generate FastMCP server from registry
  Given a registry with 9 tools registered
  When I call build_mcp_from_registry(registry, ctx)
  Then I get a FastMCP server instance
  And the server has 9 tools registered
  And each tool's name matches the registry tool name

Scenario: MCP tool invocation calls correct handler
  Given a FastMCP server built from registry
  And a connected MCP client
  When the client calls tool "search_images" with {"query": "sunset"}
  Then the registry's search_images handler is invoked
  And the result is wrapped in ToolResult with structured_content

Scenario: MCP tool error handling
  Given a FastMCP server built from registry
  When a tool handler raises ValueError("Invalid tag name")
  Then the MCP response has isError=True
  And the error message contains "Invalid tag name"

Scenario: MCP tool schema matches registry schema
  Given a registry tool "manage_tags" with action: Literal["create", "delete", "list"]
  When the MCP adapter generates the FastMCP tool
  Then the MCP tool's input schema matches the registry's input_schema
  And the "action" parameter shows enum constraint
```

## Steps

1. Create `tests/unit/test_mcp_adapter.py`
2. Create a test registry with a few simple tools (dummy handlers returning canned data, and one that raises ValueError)
3. Build a ToolContext with fake services
4. Write tests:
   - `test_build_mcp_server_tool_count` — build MCP from registry, use `await mcp.get_tools()` to verify tool count matches
   - `test_mcp_tool_invocation` — use `mcp.Client` to connect and call a tool, assert correct result returned
   - `test_mcp_tool_error_handling` — register a tool that raises ValueError, call it via MCP client, assert isError=True
   - `test_mcp_tool_schema_enum` — build MCP, get tool schema, assert action param has correct enum values
5. Import `build_mcp_from_registry` from `image_vector_search.adapters.mcp_adapter` (does not exist yet)

## Verification

```bash
pytest tests/unit/test_mcp_adapter.py -v
```

Expected: Tests fail with ImportError (Red phase).
