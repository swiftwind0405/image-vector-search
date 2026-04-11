# Task 001 — `list_images_in_folder` (Red)

**type**: test
**feature**: repository-direct-only-query
**depends-on**: []

## Objective

Add failing unit tests for a new `MetadataRepository.list_images_in_folder(path, images_root, *, limit=None, cursor=None)` method that returns only images whose direct parent directory equals `path` (i.e., no recursive descent into subfolders). The method must not yet exist — these tests must fail with `AttributeError` or similar until Task 001 impl lands.

## Files

- **Create**: `tests/unit/test_sqlite_list_images_in_folder.py`
- **Read / imitate**: `tests/unit/test_sqlite_repository.py` or whatever existing file covers `MetadataRepository` to match the repository fixture pattern.
- **Do not touch**: `src/image_vector_search/repositories/sqlite.py` (that's the Green step).

## BDD Scenarios

```gherkin
Scenario: Direct-only query excludes nested images
  Given a temp images_root "/tmp/ix"
  And the repository contains active images:
    | /tmp/ix/a/1.jpg   |
    | /tmp/ix/a/b/2.jpg |
  When I call repository.list_images_in_folder(path="a", images_root="/tmp/ix")
  Then the result contains "/tmp/ix/a/1.jpg"
  And the result does not contain "/tmp/ix/a/b/2.jpg"

Scenario: Root listing returns images directly under images_root
  Given the repository contains active images:
    | /tmp/ix/top.jpg |
    | /tmp/ix/a/1.jpg |
  When I call repository.list_images_in_folder(path="", images_root="/tmp/ix")
  Then the result contains "/tmp/ix/top.jpg"
  And the result does not contain "/tmp/ix/a/1.jpg"

Scenario: Inactive images are excluded
  Given image "/tmp/ix/a/1.jpg" exists with is_active = 0
  When I call repository.list_images_in_folder(path="a", images_root="/tmp/ix")
  Then the result does not contain that image

Scenario: Cursor pagination returns stable ordering with no duplicates
  Given 50 active images directly in "/tmp/ix/a" with distinct filenames
  When I call list_images_in_folder(path="a", images_root="/tmp/ix", limit=20)
  And then call it again passing the returned cursor (canonical_path of the last item)
  Then the two pages together contain all 50 images with no duplicates
  And the ordering is ascending by canonical_path

Scenario: Empty or non-matching folder returns empty list
  Given the repository contains only "/tmp/ix/z/1.jpg"
  When I call list_images_in_folder(path="a", images_root="/tmp/ix")
  Then the result is []
```

## Steps

1. Locate the existing SQLite repository test fixture (temp DB + `MetadataRepository` construction). Reuse it via import or copy its setup idiom — do not invent a new fixture pattern.
2. Write one `pytest` test function per scenario above. Each test:
   - Inserts image rows directly via `repository.upsert_image` (or whatever API existing repository tests use) with explicit `canonical_path` values.
   - Calls `repository.list_images_in_folder(...)` with the inputs from the scenario.
   - Asserts the expected result set (convert to a set of `canonical_path` strings for order-insensitive checks, except the pagination test which asserts ordering).
3. The pagination test must exercise at least two `list_images_in_folder` calls and concatenate results before asserting.
4. Do **not** add a matching method on `MetadataRepository`. Tests must fail on first run.

## Verification

- `pytest tests/unit/test_sqlite_list_images_in_folder.py -x` runs and **every** new test fails (expected Red).
- Failure reason must be "method does not exist" (AttributeError) — not a typo or import error unrelated to the missing method.
- No other tests in the suite regress: `pytest` still passes the rest.

## Out of scope

- Implementing `list_images_in_folder` (Task 001 impl).
- Integration-level tests with the full runtime (Task 002 covers that).
