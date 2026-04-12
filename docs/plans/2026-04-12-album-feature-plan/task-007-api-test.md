# Task 007: Album API Routes — Tests

**type**: test
**depends-on**: [006-runtime-wiring]

## Goal

Write integration tests for all album API endpoints using FastAPI's TestClient.

## BDD Scenarios

```gherkin
Scenario: Create a manual album via API
  When I POST /api/albums with {"name": "Vacation", "type": "manual"}
  Then the response status is 201
  And the response body contains the created album

Scenario: Create a smart album via API
  When I POST /api/albums with {"name": "Sunsets", "type": "smart", "rule_logic": "and"}
  Then the response status is 201

Scenario: Album name must be unique (API)
  Given an album named "My Album" exists
  When I POST /api/albums with {"name": "My Album", "type": "manual"}
  Then the response status is 409

Scenario: Album name must not be empty (API)
  When I POST /api/albums with {"name": "", "type": "manual"}
  Then the response status is 422

Scenario: List all albums
  Given 3 albums exist
  When I GET /api/albums
  Then I receive 3 albums with image_count and cover_image

Scenario: Get album detail
  Given an album with id 1 exists
  When I GET /api/albums/1
  Then I receive the album details

Scenario: Get non-existent album returns 404
  When I GET /api/albums/9999
  Then the response status is 404

Scenario: Update album
  Given an album with id 1 exists
  When I PUT /api/albums/1 with {"name": "New Name"}
  Then the response status is 200

Scenario: Delete album
  Given an album with id 1 exists
  When I DELETE /api/albums/1
  Then the response status is 204

Scenario: Add images to manual album via API
  Given a manual album and indexed images exist
  When I POST /api/albums/1/images with {"content_hashes": ["hash1", "hash2"]}
  Then the response status is 200

Scenario: Cannot add images to smart album via API
  Given a smart album exists
  When I POST /api/albums/1/images with {"content_hashes": ["hash1"]}
  Then the response status is 400

Scenario: Remove images from manual album via API
  Given a manual album with images exists
  When I DELETE /api/albums/1/images with {"content_hashes": ["hash1"]}
  Then the response status is 200

Scenario: List album images paginated
  Given a manual album with 25 images
  When I GET /api/albums/1/images?limit=10
  Then I receive 10 images and a next_cursor

Scenario: Set smart album rules via API
  Given a smart album and tags exist
  When I PUT /api/albums/1/rules with {"rules": [{"tag_id": 1, "match_mode": "include"}]}
  Then the response status is 200

Scenario: Get smart album rules via API
  Given a smart album with rules exists
  When I GET /api/albums/1/rules
  Then I receive the list of rules

Scenario: Set rule with non-existent tag returns 400
  Given a smart album exists
  When I PUT /api/albums/1/rules with {"rules": [{"tag_id": 9999, "match_mode": "include"}]}
  Then the response status is 400

Scenario: Set source paths via API
  Given a smart album exists
  When I PUT /api/albums/1/source-paths with {"paths": ["photos/travel"]}
  Then the response status is 200

Scenario: Cannot set source paths for manual album
  Given a manual album exists
  When I PUT /api/albums/1/source-paths with {"paths": ["photos/travel"]}
  Then the response status is 400
```

## Files to Create

- `tests/integration/test_album_api.py` — Integration tests using TestClient

## What to Test

Follow the pattern in `tests/integration/test_tag_api.py`:
- Create a test fixture that sets up the FastAPI app with TestClient
- Use real SQLite database (temp directory)
- Each test exercises one API endpoint scenario

## Verification

```bash
pytest tests/integration/test_album_api.py -v
# All tests should FAIL (Red) since API routes don't exist yet
```
