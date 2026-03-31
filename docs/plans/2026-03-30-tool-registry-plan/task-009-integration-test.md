# Task 009: Integration Tests

**depends-on**: ["007-app-integration"]
**type**: test
**files**:
- `tests/integration/test_tool_integration.py` (create)

## BDD Scenarios

```gherkin
Scenario: End-to-end HTTP tool invocation
  Given the full app is running with real services and test images
  When I POST /api/tools/search_images with {"query": "red"}
  Then I receive results from the real search service

Scenario: End-to-end tag management via tools
  Given the full app is running
  When I POST /api/tools/manage_tags with {"action": "create", "name": "test-tag"}
  And I POST /api/tools/tag_images with {"action": "add_tag", "content_hash": "<hash>", "tag_id": <id>}
  Then the tag is associated with the image

Scenario: MCP and HTTP return consistent results
  Given the same query "sunset"
  When I search via MCP tool and via HTTP tool
  Then both return the same results
```

## Steps

1. Create `tests/integration/test_tool_integration.py`
2. Use the existing `app_bundle` fixture pattern from `tests/integration/conftest.py` — it provides real services with fake embedding client and temp directories
3. Write tests:
   - `test_http_tool_discovery` — GET /api/tools via TestClient, assert all 9 tools listed
   - `test_http_search_images` — index test images, POST /api/tools/search_images, assert results returned
   - `test_http_manage_tags_roundtrip` — create tag, add to image, list tags on image, verify association
   - `test_http_trigger_index` — POST /api/tools/trigger_index with mode="incremental", assert job created
   - `test_mcp_http_consistency` — call search via both MCP client and HTTP, compare results

## Verification

```bash
pytest tests/integration/test_tool_integration.py -v
```

Expected: All integration tests pass.
