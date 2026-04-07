## Test image fixtures

This directory stores small, committed image fixtures used by automated tests.

The deterministic fixture dataset lives under `tests/fixtures/images/auto/`.
Those files are generated once, checked into the repository, and kept stable so
tests can exercise duplicate content, renamed paths, nested folders, spaces, and
non-ASCII path segments without depending on external image sources.

Use these committed fixtures for automated tests. For manual validation with
real images, build a local-only dataset under `sample-data/demo-set/` with
`scripts/build_demo_image_set.py` instead of committing additional image files.
