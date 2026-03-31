# Task 004: Index & Image Tools — Tests

**depends-on**: ["001-registry-core-impl"]
**type**: test
**files**:
- `tests/unit/test_index_tools.py` (create)

## BDD Scenarios

```gherkin
Scenario: Get index status
  Given a ToolContext with a StatusService
  When I call get_index_status tool with {}
  Then it returns a dict with index statistics including images_on_disk, total_images, active_images

Scenario: Trigger incremental index
  Given a ToolContext with a JobRunner
  When I call trigger_index with {"mode": "incremental"}
  Then it returns a dict with "job" containing the enqueued JobRecord

Scenario: List images with filter
  Given a ToolContext with a StatusService containing images
  When I call list_images with {"folder": "vacation"}
  Then it returns a dict with "images" filtered to the folder

Scenario: Get single image info
  Given a ToolContext with a StatusService
  When I call get_image_info with {"content_hash": "abc123"}
  Then it returns a dict with image metadata including tags and categories
```

## Steps

1. Create `tests/unit/test_index_tools.py` with `FakeStatusService` and `FakeJobRunner`
2. Write tests:
   - `test_get_index_status` — call tool, assert returns dict with expected status fields
   - `test_trigger_index_incremental` — call with mode="incremental", assert JobRecord returned
   - `test_trigger_index_full_rebuild` — call with mode="full_rebuild", assert JobRecord returned
   - `test_list_images` — call with no filter, assert images list returned
   - `test_list_images_with_folder` — call with folder param, assert filtered
   - `test_get_image_info` — call with content_hash, assert image record with tags/categories
   - `test_get_image_info_not_found` — call with unknown hash, assert ValueError

## Verification

```bash
pytest tests/unit/test_index_tools.py -v
```

Expected: Tests fail with ImportError (Red phase).
