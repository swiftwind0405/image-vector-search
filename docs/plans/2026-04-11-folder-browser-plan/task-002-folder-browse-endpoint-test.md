# Task 002 — `GET /api/folders/browse` (Red)

**type**: test
**feature**: folder-browse-endpoint
**depends-on**: ["001-impl"]

## Objective

Add failing integration tests for a new `GET /api/folders/browse` admin endpoint that returns `{path, parent, folders, images, next_cursor}`. The endpoint must not yet exist — tests must fail with 404 or routing error until Task 002 impl lands. Task 001 impl is required because the route will call `list_images_in_folder`.

## Files

- **Create**: `tests/integration/test_folder_browser_api.py`
- **Read / imitate**: `tests/integration/conftest.py` and any existing admin-route integration test (e.g., `test_web_admin.py`) to reuse the authenticated client fixture and the temp `images_root` wiring.
- **Do not touch**: `src/image_vector_search/api/*`, `src/image_vector_search/app.py`.

## BDD Scenarios

```gherkin
Scenario: Root-level browse returns top-level folders and root-level images
  Given the index contains active images:
    | <images_root>/a/1.jpg       |
    | <images_root>/a/b/2.jpg     |
    | <images_root>/a/b/c/3.jpg   |
    | <images_root>/top.jpg       |
  When I GET /api/folders/browse
  Then the response status is 200
  And response.path is ""
  And response.parent is null
  And response.folders is ["a"]
  And response.images contains exactly the image with canonical_path "<images_root>/top.jpg"

Scenario: Mid-level browse returns only immediate subfolders and direct images
  Given the index contains active images:
    | <images_root>/a/1.jpg     |
    | <images_root>/a/b/2.jpg   |
    | <images_root>/a/b/c/3.jpg |
    | <images_root>/a/d/4.jpg   |
  When I GET /api/folders/browse?path=a
  Then response.path is "a"
  And response.parent is ""
  And response.folders is ["a/b", "a/d"]
  And response.images contains exactly "<images_root>/a/1.jpg"

Scenario: Leaf folder returns no subfolders
  Given the index contains "<images_root>/a/b/c/3.jpg"
  When I GET /api/folders/browse?path=a/b/c
  Then response.folders is []
  And response.images contains "<images_root>/a/b/c/3.jpg"

Scenario: Non-existent folder returns empty result
  When I GET /api/folders/browse?path=does/not/exist
  Then response status is 200
  And response.folders is []
  And response.images is []

Scenario: Path traversal attempt is rejected
  When I GET /api/folders/browse?path=../etc
  Then the response status is 400

Scenario: Absolute path is rejected
  When I GET /api/folders/browse?path=/etc/passwd
  Then the response status is 400

Scenario: Leading and trailing slashes are normalized
  Given the index contains "<images_root>/a/1.jpg"
  When I GET /api/folders/browse?path=/a/
  Then response.path is "a"
  And response.images contains the image

Scenario: Inactive images are excluded
  Given "<images_root>/a/1.jpg" exists with is_active = 0
  When I GET /api/folders/browse?path=a
  Then response.images does not contain that image

Scenario: Images in deeper subfolders do not leak into the parent view
  Given the index contains only "<images_root>/a/b/2.jpg"
  When I GET /api/folders/browse?path=a
  Then response.folders is ["a/b"]
  And response.images is []

Scenario: Authentication is required
  Given no admin session cookie is set
  When I GET /api/folders/browse
  Then the response matches how existing admin routes reject unauthenticated requests (401 or redirect)
```

## Steps

1. Inspect `tests/integration/conftest.py` and at least one existing admin-route integration test to understand:
   - How the temp images_root is constructed.
   - How authenticated vs unauthenticated clients are obtained.
   - How images are inserted into the repository before the request.
2. Create `tests/integration/test_folder_browser_api.py` with one test function per scenario, using the existing authenticated client fixture.
3. For assertions, parse the JSON response and compare against expected dicts/lists. The `images` list equality check should compare only `canonical_path` values to stay resilient to unrelated `ImageRecord` fields.
4. For the auth scenario, copy the approach used by an existing admin-route auth test — do not reinvent the 401/redirect check.
5. Do **not** create the route. All tests must fail initially (most with 404 or "no route matches").

## Verification

- `pytest tests/integration/test_folder_browser_api.py -x` — every new test fails (Red).
- Failure reason: route does not exist (FastAPI 404), not a test-setup error.
- `pytest tests/ -k "not folder_browser"` — rest of the suite still passes.

## Out of scope

- Implementing the route (Task 002 impl).
- Frontend work (Task 003).
