# Task 002: Search Tools — Tests

**depends-on**: ["001-registry-core-impl"]
**type**: test
**files**:
- `tests/unit/test_search_tools.py` (create)

## BDD Scenarios

```gherkin
Scenario: Execute a search tool
  Given a ToolContext with a SearchService containing indexed images
  And the tool "search_images" is registered
  When I call the tool with {"query": "sunset", "top_k": 3}
  Then it returns a dict with "results" containing up to 3 SearchResult items
  And each result has content_hash, path, score, width, height, mime_type

Scenario: Execute search_similar tool
  Given a ToolContext with a SearchService
  And the tool "search_similar" is registered
  When I call the tool with {"image_path": "/images/test.jpg", "top_k": 2}
  Then it returns a dict with "results" containing similar image results
```

## Steps

1. Create `tests/unit/test_search_tools.py`
2. Create a `FakeSearchService` that returns canned SearchResult objects
3. Create a `fake_tool_context` fixture that builds a ToolContext with fake services
4. Write tests:
   - `test_search_images_tool` — call `search_images(ctx, query="sunset", top_k=3)`, assert returns dict with "results" key, results have correct fields
   - `test_search_similar_tool` — call `search_similar(ctx, image_path="/images/test.jpg", top_k=2)`, assert returns dict with "results"
5. Import tool functions from `image_search_mcp.tools.search_tools` (does not exist yet)

## Verification

```bash
pytest tests/unit/test_search_tools.py -v
```

Expected: Tests fail with ImportError (Red phase).
