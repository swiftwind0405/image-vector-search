# Task 001 — `list_images_in_folder` (Green)

**type**: impl
**feature**: repository-direct-only-query
**depends-on**: ["001-test"]

## Objective

Implement `MetadataRepository.list_images_in_folder(path, images_root, *, limit=None, cursor=None)` so that the tests from Task 001 test pass. The method returns active images whose direct parent directory equals the normalized `path`, using a SQL predicate that relies on the existing `canonical_path` prefix scan plus an `instr`-based direct-child check.

## Files

- **Modify**: `src/image_vector_search/repositories/sqlite.py`
- **Do not touch**: `tests/unit/test_sqlite_list_images_in_folder.py` (already written in Red).

## BDD Scenarios

See Task 001 test for the full Gherkin. All five scenarios must pass after this task. Summarized:

```gherkin
Scenario: Direct-only query excludes nested images
Scenario: Root listing returns images directly under images_root
Scenario: Inactive images are excluded
Scenario: Cursor pagination returns stable ordering with no duplicates
Scenario: Empty or non-matching folder returns empty list
```

## Steps

1. Open `src/image_vector_search/repositories/sqlite.py`; locate the existing listing methods (e.g., `list_active_images`, `list_folders`) to match their style (connection usage, row → model mapping, cursor encoding).
2. Add `list_images_in_folder(self, path, images_root, *, limit=None, cursor=None)`:
   - Normalize `path` by stripping leading/trailing `/`; compute `prefix = images_root.rstrip("/") + "/"` if `path == ""` else `images_root.rstrip("/") + "/" + path + "/"`.
   - Escape SQL `LIKE` metacharacters (`%`, `_`, `\`) in the `prefix` value and use `ESCAPE '\\'` in the SQL, so that a folder literally named `a_b` does not match `axb`.
   - Run SQL:
     ```
     SELECT * FROM images
     WHERE is_active = 1
       AND canonical_path LIKE :prefix ESCAPE '\\'
       AND instr(substr(canonical_path, length(:prefix_no_wild) + 1), '/') = 0
       AND (:cursor IS NULL OR canonical_path > :cursor)
     ORDER BY canonical_path ASC
     LIMIT :limit
     ```
     where `:prefix` is `prefix + '%'` and `:prefix_no_wild` is `prefix`. If `limit is None`, omit the `LIMIT` clause.
   - Map each row through the same `ImageRecord` constructor the other listing methods use.
   - Return the list (not a cursor tuple — pagination is caller-driven via the explicit `cursor` parameter, mirroring existing methods).
3. Run the Task 001 test file.

## Verification

- `pytest tests/unit/test_sqlite_list_images_in_folder.py -x` — all tests pass (Green).
- `pytest` — the full suite still passes; no other repository test regressed.
- `python -c "from image_vector_search.repositories.sqlite import MetadataRepository; print(MetadataRepository.list_images_in_folder)"` resolves without error.

## Out of scope

- Exposing this via an HTTP endpoint (Task 002).
- Changing the signature or semantics of any existing repository method.
- Schema changes or migrations.
