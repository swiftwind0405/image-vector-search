# Task 002 — `GET /api/folders/browse` (Green)

**type**: impl
**feature**: folder-browse-endpoint
**depends-on**: ["002-test"]

## Objective

Implement the `GET /api/folders/browse` endpoint so all Task 002 tests pass. The route lives in a new admin router, is wired into `app.py`, and uses `MetadataRepository.list_folders` (existing) and `MetadataRepository.list_images_in_folder` (from Task 001 impl) to assemble its response. No other admin routers are modified.

## Files

- **Create**: `src/image_vector_search/api/admin_folder_routes.py`
- **Modify**: `src/image_vector_search/app.py` (include the new router next to the other admin routers, gated on `runtime_services` / `repository` availability — same pattern as `create_admin_settings_router`).
- **Read / imitate**:
  - `src/image_vector_search/api/admin_routes.py` for router factory style, `JSONResponse(jsonable_encoder(...))` usage, and pagination/cursor patterns.
  - `src/image_vector_search/api/admin_bulk_routes.py` for the `list_folders` reuse pattern (`tag_service._repo.list_folders(images_root)`).
- **Do not touch**: `tests/integration/test_folder_browser_api.py`.

## BDD Scenarios

All Task 002 test scenarios must pass. Full Gherkin is in Task 002 test; summarized here:

```gherkin
Scenario: Root-level browse returns top-level folders and root-level images
Scenario: Mid-level browse returns only immediate subfolders and direct images
Scenario: Leaf folder returns no subfolders
Scenario: Non-existent folder returns empty result
Scenario: Path traversal attempt is rejected
Scenario: Absolute path is rejected
Scenario: Leading and trailing slashes are normalized
Scenario: Inactive images are excluded
Scenario: Images in deeper subfolders do not leak into the parent view
Scenario: Authentication is required
```

## Steps

1. **Create router module** `src/image_vector_search/api/admin_folder_routes.py` exporting `create_admin_folder_router(*, repository, status_service, images_root)`:
   - Inner `GET /api/folders/browse` handler with query params `path: str = ""`, `limit: int | None = None`, `cursor: str | None = None`.
   - **Normalize `path`**: strip leading/trailing `/`. Reject with `HTTPException(400, "invalid path")` if the normalized value:
     - Contains `..` as a path segment
     - Contains backslash, NUL byte
     - Was originally an absolute path (i.e., raw value started with `/` and after strip is non-empty — actually simpler: reject raw path containing `..` or `\\`; the leading `/` case is handled by always stripping).
     - **Correction**: absolute path rejection must fire for inputs like `/etc/passwd`. After stripping leading `/`, that becomes `etc/passwd`, which looks valid. Detect the absolute case by checking the **raw** input for a leading `/` combined with a path that would escape the archive, OR simply reject any raw input that begins with `/` followed by a segment that does not exist as a known folder. Simpler: **reject raw input starting with `/` that is longer than 1 char**, before stripping. `/` alone (or empty) is allowed and means root.
   - **Compute subfolders**: call `repository.list_folders(images_root)` → filter entries:
     - At root: entries with no `/` inside.
     - Non-root: entries matching `entry == path + "/" + <single_segment>` (startswith `path + "/"` AND the remainder contains no further `/`).
     - Sort ascending.
   - **Compute images**: call `repository.list_images_in_folder(path, images_root, limit=limit, cursor=cursor)`.
   - **Parent**: `None` if `path == ""`, else `path.rsplit("/", 1)[0]` (which yields `""` when there's no parent folder above).
   - **Next cursor**: if `limit` was provided and the image list has exactly `limit` items, set `next_cursor = images[-1].canonical_path`; else `None`.
   - Return `JSONResponse(content=jsonable_encoder({"path": path, "parent": parent, "folders": subfolders, "images": images, "next_cursor": next_cursor}))`.
2. **Wire into `app.py`**: after the existing `create_admin_settings_router` block, include the new router when `runtime_services is not None and repository is not None`. Pass `images_root=str(app_settings.images_root)`. This places the route inside the authenticated admin area automatically because all admin routers share the same `SessionMiddleware`.
3. **Verify locally**: run the Task 002 test file.
4. **Run full suite**: ensure no regressions.

## Verification

- `pytest tests/integration/test_folder_browser_api.py -x` — all scenarios pass (Green).
- `pytest` — full suite passes.
- `python -c "from image_vector_search.api.admin_folder_routes import create_admin_folder_router"` resolves.
- Manual smoke (optional here, mandatory in Task 003): hit the endpoint with `curl` against a running dev server and inspect the JSON.

## Out of scope

- Frontend work (Task 003).
- Changes to `/api/folders`, `/api/images`, or bulk routes.
- Adding a database index on `canonical_path` (out of scope unless profiling forces it).
