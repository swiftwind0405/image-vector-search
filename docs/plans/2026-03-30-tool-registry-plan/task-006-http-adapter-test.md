# Task 006: HTTP Tool Adapter — Tests

**depends-on**: ["001-registry-core-impl"]
**type**: test
**files**:
- `tests/unit/test_http_adapter.py` (create)

## BDD Scenarios

```gherkin
Scenario: Tool discovery endpoint
  Given a registry with tools "search_images", "manage_tags"
  When I GET /api/tools
  Then I receive a JSON array with 2 objects
  And each object has "name", "description", and "parameters" fields
  And "parameters" is a valid JSON Schema

Scenario: Invoke tool via HTTP
  Given a registry with "search_images" tool
  When I POST /api/tools/search_images with body {"query": "sunset", "top_k": 5}
  Then I receive HTTP 200
  And the response body matches the tool's return value

Scenario: Invoke nonexistent tool via HTTP
  Given a registry without a "nonexistent" tool
  When I POST /api/tools/nonexistent with body {}
  Then I receive HTTP 404
  And the response contains "Tool 'nonexistent' not found"

Scenario: HTTP error mapping for ValueError
  Given a tool that raises ValueError("name is required")
  When I POST /api/tools/manage_tags with {"action": "create"}
  Then I receive HTTP 400
  And the response body contains "name is required"

Scenario: HTTP error mapping for FileNotFoundError
  Given a tool that raises FileNotFoundError
  When I POST /api/tools/search_similar with {"image_path": "/nonexistent.jpg"}
  Then I receive HTTP 404
```

## Steps

1. Create `tests/unit/test_http_adapter.py`
2. Create a test registry with dummy tools (one returning data, one raising ValueError, one raising FileNotFoundError)
3. Build a ToolContext with fake services
4. Use `build_tool_router` to create the router, mount on a test FastAPI app
5. Use `httpx.AsyncClient` or `fastapi.testclient.TestClient` to make requests
6. Write tests:
   - `test_discovery_endpoint` — GET /api/tools, assert 200, array with name/description/parameters
   - `test_invoke_tool_success` — POST /api/tools/search_images, assert 200 with expected response
   - `test_invoke_nonexistent_tool` — POST /api/tools/nonexistent, assert 404
   - `test_invoke_tool_value_error` — POST tool that raises ValueError, assert 400
   - `test_invoke_tool_file_not_found` — POST tool that raises FileNotFoundError, assert 404
7. Import `build_tool_router` from `image_vector_search.adapters.http_tool_adapter` (does not exist yet)

## Verification

```bash
pytest tests/unit/test_http_adapter.py -v
```

Expected: Tests fail with ImportError (Red phase).
