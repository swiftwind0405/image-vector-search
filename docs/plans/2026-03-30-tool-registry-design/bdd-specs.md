# BDD Specifications

## Feature: Tool Registry

### Scenario: Register a tool via decorator
```gherkin
Given an empty ToolRegistry
When I decorate an async function with @registry.tool(name="my_tool", description="Does things")
Then the registry contains a tool named "my_tool"
And the tool's description is "Does things"
And the tool's handler is the decorated function
```

### Scenario: Infer input schema from type hints
```gherkin
Given a function with parameters (query: str, top_k: int = 5, folder: str | None = None)
When I register it as a tool
Then the input schema has "query" as a required string property
And "top_k" as an optional integer property with default 5
And "folder" as an optional nullable string property
```

### Scenario: Infer schema for Literal action parameter
```gherkin
Given a function with parameter action: Literal["create", "delete", "list"]
When I register it as a tool
Then the input schema has "action" as a required string with enum ["create", "delete", "list"]
```

### Scenario: Exclude ToolContext from schema
```gherkin
Given a function with first parameter ctx: ToolContext
When I register it as a tool
Then the input schema does not contain a "ctx" property
And the schema only includes user-facing parameters
```

### Scenario: List all registered tools
```gherkin
Given a registry with tools "search_images", "manage_tags", "get_index_status"
When I call registry.get_tools()
Then I receive 3 ToolDef objects
And each has name, description, fn, and input_schema fields
```

### Scenario: Get tool by name
```gherkin
Given a registry with a tool named "search_images"
When I call registry.get_tool("search_images")
Then I receive the ToolDef for "search_images"
When I call registry.get_tool("nonexistent")
Then I receive None
```

## Feature: Tool Execution

### Scenario: Execute a search tool
```gherkin
Given a ToolContext with a SearchService containing indexed images
And the tool "search_images" is registered
When I call the tool with {"query": "sunset", "top_k": 3}
Then it returns a dict with "results" containing up to 3 SearchResult items
And each result has content_hash, path, score, width, height, mime_type
```

### Scenario: Execute manage_tags with action=create
```gherkin
Given a ToolContext with a TagService
And the tool "manage_tags" is registered
When I call the tool with {"action": "create", "name": "landscape"}
Then it returns a dict with "tag" containing the created Tag
And the tag has an id, name "landscape", and created_at timestamp
```

### Scenario: Execute manage_tags with action=list
```gherkin
Given a ToolContext with a TagService containing tags "landscape", "portrait"
When I call manage_tags with {"action": "list"}
Then it returns {"tags": [...]} with 2 tag objects
```

### Scenario: Tool raises ValueError for invalid input
```gherkin
Given the tool "manage_tags" is registered
When I call it with {"action": "create"} (missing required "name")
Then it raises ValueError with a message indicating "name" is required
```

### Scenario: Tool raises ValueError for empty tag name
```gherkin
Given the tool "manage_tags" is registered
When I call it with {"action": "create", "name": ""}
Then it raises ValueError with a message about empty name
```

## Feature: MCP Adapter

### Scenario: Generate FastMCP server from registry
```gherkin
Given a registry with 9 tools registered
When I call build_mcp_from_registry(registry, ctx)
Then I get a FastMCP server instance
And the server has 9 tools registered
And each tool's name matches the registry tool name
```

### Scenario: MCP tool invocation calls correct handler
```gherkin
Given a FastMCP server built from registry
And a connected MCP client
When the client calls tool "search_images" with {"query": "sunset"}
Then the registry's search_images handler is invoked
And the result is wrapped in ToolResult with structured_content
```

### Scenario: MCP tool error handling
```gherkin
Given a FastMCP server built from registry
When a tool handler raises ValueError("Invalid tag name")
Then the MCP response has isError=True
And the error message contains "Invalid tag name"
```

### Scenario: MCP tool schema matches registry schema
```gherkin
Given a registry tool "manage_tags" with action: Literal["create", "delete", "list"]
When the MCP adapter generates the FastMCP tool
Then the MCP tool's input schema matches the registry's input_schema
And the "action" parameter shows enum constraint
```

## Feature: HTTP Tool Adapter

### Scenario: Tool discovery endpoint
```gherkin
Given a registry with tools "search_images", "manage_tags"
When I GET /api/tools
Then I receive a JSON array with 2 objects
And each object has "name", "description", and "parameters" fields
And "parameters" is a valid JSON Schema
```

### Scenario: Invoke tool via HTTP
```gherkin
Given a registry with "search_images" tool
When I POST /api/tools/search_images with body {"query": "sunset", "top_k": 5}
Then I receive HTTP 200
And the response body matches the tool's return value
```

### Scenario: Invoke nonexistent tool via HTTP
```gherkin
Given a registry without a "nonexistent" tool
When I POST /api/tools/nonexistent with body {}
Then I receive HTTP 404
And the response contains "Tool 'nonexistent' not found"
```

### Scenario: HTTP error mapping for ValueError
```gherkin
Given a tool that raises ValueError("name is required")
When I POST /api/tools/manage_tags with {"action": "create"}
Then I receive HTTP 400
And the response body contains "name is required"
```

### Scenario: HTTP error mapping for FileNotFoundError
```gherkin
Given a tool that raises FileNotFoundError
When I POST /api/tools/search_similar with {"image_path": "/nonexistent.jpg"}
Then I receive HTTP 404
```

## Feature: OpenClaw Integration

### Scenario: OpenClaw agent discovers tools
```gherkin
Given the image-search server is running at $IMAGE_SEARCH_URL
When an OpenClaw agent fetches GET $IMAGE_SEARCH_URL/api/tools
Then it receives a list of available tools with schemas
And can determine which tool to call based on descriptions
```

### Scenario: OpenClaw agent searches images
```gherkin
Given the image-search server has indexed images
When an OpenClaw agent POSTs to /api/tools/search_images
  with body {"query": "red flowers in garden", "top_k": 3}
Then it receives results with image paths and similarity scores
And can present these to the user
```

### Scenario: OpenClaw agent manages tags end-to-end
```gherkin
Given the image-search server is running
When an OpenClaw agent:
  1. POSTs /api/tools/manage_tags with {"action": "create", "name": "vacation"}
  2. POSTs /api/tools/search_images with {"query": "beach sunset"}
  3. POSTs /api/tools/tag_images with {"action": "add", "content_hash": "<hash>", "tag_id": 1}
Then the image is tagged with "vacation"
And subsequent searches can filter by this tag
```

## Testing Strategy

### Unit Tests
- `test_registry.py`: Test `ToolRegistry` — registration, schema extraction, get_tools/get_tool
- `test_tools.py`: Test each tool function directly with mocked ToolContext
- `test_mcp_adapter.py`: Test `build_mcp_from_registry` generates correct FastMCP server
- `test_http_adapter.py`: Test HTTP router with TestClient

### Integration Tests
- `test_tool_integration.py`: End-to-end flow through HTTP adapter → registry → services → real DB
- `test_mcp_tool_integration.py`: MCP client → adapter → registry → services

### Test Fixtures
```python
@pytest.fixture
def fake_tool_context():
    """ToolContext with fake services for unit testing."""
    return ToolContext(
        search_service=FakeSearchService(),
        tag_service=FakeTagService(),
        status_service=FakeStatusService(),
        job_runner=FakeJobRunner(),
        settings=Settings(images_root="/tmp/test-images", ...),
    )

@pytest.fixture
def registry_with_tools():
    """Registry with all tools registered."""
    from image_vector_search.tools import default_registry
    return default_registry
```
