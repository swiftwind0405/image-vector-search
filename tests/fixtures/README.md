## Test image fixtures

This directory stores small, committed image fixtures used by automated tests.

The deterministic fixture dataset lives under `tests/fixtures/images/auto/`.
Those files are generated once, checked into the repository, and kept stable so
tests can exercise duplicate content, renamed paths, nested folders, spaces, and
non-ASCII path segments without depending on external image sources.

Use these committed fixtures for automated tests. For manual validation with
real images, build a local-only dataset outside the committed fixture tree with
`scripts/build_demo_image_set.py` instead of committing additional image files.

Example:

```bash
.venv/bin/python scripts/build_demo_image_set.py \
  --source /path/to/local/images \
  --output tmp/demo-set
```

The script copies up to 24 images by default, preserves relative paths, and
writes `manifest.json` under the chosen output directory.
