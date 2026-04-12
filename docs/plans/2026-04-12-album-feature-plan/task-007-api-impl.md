# Task 007: Album API Routes — Implementation

**type**: impl
**depends-on**: [007-api-test, 005-cover-image-impl]

## Goal

Implement all album API endpoints and wire the router into the FastAPI app.

## Files to Create

- `src/image_vector_search/api/admin_album_routes.py` — All album API route handlers

## Files to Modify

- `src/image_vector_search/app.py` — Include the album router

## What to Implement

### API Routes (`admin_album_routes.py`)

Create a router factory function following `admin_tag_routes.py` pattern. Define Pydantic request/response models inline:

- `CreateAlbumRequest`, `UpdateAlbumRequest`, `AddImagesRequest`, `RemoveImagesRequest`, `AlbumRuleInput`, `SetRulesRequest`, `SetSourcePathsRequest`

Implement 12 endpoints:

| Method | Path | Handler | Status |
|--------|------|---------|--------|
| POST | `/api/albums` | Create album | 201 |
| GET | `/api/albums` | List albums | 200 |
| GET | `/api/albums/{album_id}` | Get album | 200/404 |
| PUT | `/api/albums/{album_id}` | Update album | 200/404 |
| DELETE | `/api/albums/{album_id}` | Delete album | 204/404 |
| GET | `/api/albums/{album_id}/images` | List images | 200 |
| POST | `/api/albums/{album_id}/images` | Add images | 200/400 |
| DELETE | `/api/albums/{album_id}/images` | Remove images | 200/400 |
| GET | `/api/albums/{album_id}/rules` | Get rules | 200 |
| PUT | `/api/albums/{album_id}/rules` | Set rules | 200/400 |
| GET | `/api/albums/{album_id}/source-paths` | Get source paths | 200 |
| PUT | `/api/albums/{album_id}/source-paths` | Set source paths | 200/400 |

Error mapping:
- `ValueError` → 400 HTTPException
- `sqlite3.IntegrityError` → 409 HTTPException
- Album not found → 404 HTTPException

### App Wiring (`app.py`)

Import and include the album router, following the pattern used for tag routes. Conditional on `album_service` being available in runtime.

## Verification

```bash
pytest tests/integration/test_album_api.py -v
# All API tests should PASS (Green)
```
