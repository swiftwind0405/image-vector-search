# Test Image Dataset Design

**Date:** 2026-04-07

**Goal:** Add a reproducible test image dataset for automated testing and a separate small demo dataset workflow for local manual validation.

## Context

The current test suite mostly generates temporary images with `PIL.Image.new(...)` inside fixtures. That keeps tests stable, but it does not provide a reusable fixture set for broader indexing, filesystem-path, and demo workflows.

The project identifies images by content hash, not file path. The dataset therefore needs to exercise both semantic-search-oriented cases and filesystem/indexing behavior such as duplicate content, renames, nested folders, and special path names.

## Requirements

- Keep repository data small and reproducible.
- Support automated tests with deterministic expectations.
- Support local demo/manual validation with a generated sample set from an existing image library.
- Avoid checking large or copyrighted real-world image corpora into git.

## Chosen Approach

Use a mixed strategy:

1. Commit a small, programmatically generated fixture set into the repository for automated tests.
2. Add a script that can generate a small local demo set by sampling from a user-provided image directory.

This balances reproducibility, repository size, and real-world validation.

## Deliverables

### 1. Fixed automated fixture set

Add a repository-owned fixture directory under `tests/fixtures/images/auto/`.

This set should contain roughly 12-16 images and cover:

- Simple color-driven semantic cases matching the current fake embedding behavior
- Duplicate-content images at different paths
- Rename/move scenarios with identical file bytes
- Nested directories
- Paths containing spaces and Chinese characters
- Extension-case differences such as `.JPG`
- Near-duplicate but byte-distinct variants

### 2. Fixture documentation

Add `tests/fixtures/README.md` describing each image and why it exists.

### 3. Demo dataset builder

Add `scripts/build_demo_image_set.py` that:

- Accepts a source image directory
- Copies a sampled subset into a generated demo directory
- Defaults to a small set of about 24 images
- Preserves a limited amount of relative folder structure
- Writes a manifest recording source path, destination path, size, and content hash

### 4. Test coverage

Add or update integration tests so the fixed fixture set is exercised directly, not only via ad hoc image creation.

Coverage should include:

- Indexing nested folders from fixture directories
- Duplicate detection by content hash
- Search returning expected color-oriented matches
- Special-path handling for spaces and non-ASCII names

## Alternatives Considered

### Script-only generation

Rejected because it hides the canonical test corpus and makes debugging less transparent.

### Commit a large static image set

Rejected because it increases repository size and introduces long-term maintenance and licensing concerns.

## Directory Layout

```text
tests/
  fixtures/
    README.md
    images/
      auto/
scripts/
  build_demo_image_set.py
sample-data/
  README.md
```

## Sample Naming Guidance

- Use descriptive names such as `red-square.png` and `orange-wide.jpg`.
- Use consistent prefixes for duplicate-content cases.
- Keep most paths simple, while preserving a few edge-case names for path handling.

## Testing Strategy

- Continue using temporary directories during tests.
- Copy fixture images from `tests/fixtures/images/auto/` into the temp `images_root` used by integration tests.
- Keep assertions focused on stable outcomes: counts, deduplication, path normalization, and expected first-result colors.

## Risks

- If fixture images are too synthetic, they will not be representative for manual demo use.
- If the fixture set becomes too large, tests will slow down and repo weight will grow.

## Mitigations

- Keep the committed dataset minimal and purpose-built.
- Use the demo builder for manual validation on real local images instead of expanding committed fixtures.
