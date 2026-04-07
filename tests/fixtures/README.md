## Test image fixtures

This directory stores small, committed image fixtures used by automated tests.

The deterministic fixture dataset lives under `tests/fixtures/images/auto/`.
Those files are generated once, checked into the repository, and kept stable so
tests can exercise duplicate content, renamed paths, nested folders, spaces, and
non-ASCII path segments without depending on external image sources.
