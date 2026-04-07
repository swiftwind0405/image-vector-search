## Demo image data

This directory is reserved for locally generated demo datasets used for manual
validation.

Demo images are generated from a local source directory instead of being
committed, so the repository stays small and free of personal or licensed image
content.

Generate a local demo set with:

```bash
.venv/bin/python scripts/build_demo_image_set.py \
  --source /path/to/local/images \
  --output sample-data/demo-set
```

The builder copies up to 24 images by default, preserves relative paths, and
writes `sample-data/demo-set/manifest.json` with SHA-256 checksums for the
copied files.

Generated demo data under `sample-data/demo-set/` is for local validation only
and should not be committed.

Expected layout:

- `sample-data/demo-set/` for generated demo images
- `sample-data/demo-set/manifest.json` for copied-file metadata
- `sample-data/README.md` for usage notes
