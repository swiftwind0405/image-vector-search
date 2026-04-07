# Test Image Dataset Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reproducible automated test image dataset plus a small local demo dataset builder for manual validation.

**Architecture:** Keep committed repository fixtures small and deterministic by generating them programmatically once and storing the resulting files under `tests/fixtures/images/auto/`. Add a standalone script that samples real images from a local source directory into `sample-data/demo-set/` with a manifest so manual validation can use realistic images without checking them into git.

**Tech Stack:** Python, Pillow, pytest, existing integration fixtures, pathlib, hashlib, shutil, json

---

### Task 1: Add fixture documentation and repository-owned sample layout

**Files:**
- Create: `tests/fixtures/README.md`
- Create: `sample-data/README.md`

**Step 1: Write the failing test**

Add a documentation-oriented repository test in `tests/unit/test_readme.py` or a new small test file that asserts the fixture readme paths exist.

```python
from pathlib import Path


def test_fixture_docs_exist() -> None:
    assert Path("tests/fixtures/README.md").exists()
    assert Path("sample-data/README.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_readme.py -k fixture_docs_exist -v`
Expected: FAIL because the new README files do not exist yet.

**Step 3: Write minimal implementation**

Create concise README files that explain:

- What the committed fixture set is for
- Why demo images are generated locally instead of committed
- Expected directories

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_readme.py -k fixture_docs_exist -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/README.md sample-data/README.md tests/unit/test_readme.py
git commit -m "docs: add test image dataset notes"
```

### Task 2: Add deterministic fixture images for automated tests

**Files:**
- Create: `tests/fixtures/images/auto/red-square.png`
- Create: `tests/fixtures/images/auto/orange-wide.jpg`
- Create: `tests/fixtures/images/auto/blue-tall.png`
- Create: `tests/fixtures/images/auto/green-small.jpg`
- Create: `tests/fixtures/images/auto/dup/content-same-orange-a.jpg`
- Create: `tests/fixtures/images/auto/dup/content-same-orange-b.jpg`
- Create: `tests/fixtures/images/auto/renamed/before/orange.jpg`
- Create: `tests/fixtures/images/auto/renamed/after/orange-renamed.jpg`
- Create: `tests/fixtures/images/auto/folders/2024/travel/red sunset.jpg`
- Create: `tests/fixtures/images/auto/folders/2024/人物/blue-portrait.png`
- Create: `tests/fixtures/images/auto/folders/misc/green_leaf.JPG`
- Create: `tests/fixtures/images/auto/variants/orange-border.png`

**Step 1: Write the failing test**

Add a new unit test file, for example `tests/unit/test_test_fixtures.py`, that asserts the expected fixture files exist and that duplicate-content pairs really share the same SHA-256.

```python
import hashlib
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_auto_fixture_images_exist() -> None:
    root = Path("tests/fixtures/images/auto")
    assert (root / "red-square.png").exists()
    assert (root / "dup/content-same-orange-a.jpg").exists()


def test_duplicate_fixture_pairs_share_hash() -> None:
    root = Path("tests/fixtures/images/auto")
    assert _sha256(root / "dup/content-same-orange-a.jpg") == _sha256(
        root / "dup/content-same-orange-b.jpg"
    )
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_test_fixtures.py -v`
Expected: FAIL because the fixture files do not exist yet.

**Step 3: Write minimal implementation**

Generate the fixture images with Pillow once, store them in the repository, and keep their byte identity intentional:

- Exact duplicates should be byte-for-byte identical
- Rename fixtures should also be byte-for-byte identical
- Variant fixtures should differ in content while staying visually close

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_test_fixtures.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/images/auto tests/unit/test_test_fixtures.py
git commit -m "test: add deterministic image fixtures"
```

### Task 3: Teach integration tests to use the committed fixtures

**Files:**
- Modify: `tests/integration/conftest.py`
- Create: `tests/integration/test_fixture_dataset.py`

**Step 1: Write the failing test**

Add a fixture-copy helper and a new integration test that copies the committed fixture tree into the temp `images_root`, runs indexing, and verifies deduplication plus special-path handling.

```python
async def test_indexing_committed_fixture_dataset(app_bundle, copy_auto_fixture_tree):
    copy_auto_fixture_tree()

    job = app_bundle.job_runner.enqueue_scan()
    completed = app_bundle.job_runner.run_next()

    assert completed is not None
    assert app_bundle.repository.count_images() > 0
```

Add stronger assertions for:

- Duplicate content is only embedded once per content hash
- Images with spaces and Chinese path segments are indexed
- Search for `orange` returns an orange fixture near the top

**Step 2: Run test to verify it fails**

Run: `pytest tests/integration/test_fixture_dataset.py -v`
Expected: FAIL because the helper and/or fixture data are not wired in yet.

**Step 3: Write minimal implementation**

Update `tests/integration/conftest.py` with a helper fixture that copies `tests/fixtures/images/auto/` into the temp `images_root` using `shutil.copytree(..., dirs_exist_ok=True)`, then implement the integration test with stable assertions.

**Step 4: Run test to verify it passes**

Run: `pytest tests/integration/test_fixture_dataset.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/conftest.py tests/integration/test_fixture_dataset.py
git commit -m "test: exercise committed image fixture dataset"
```

### Task 4: Add a local demo dataset builder script

**Files:**
- Create: `scripts/build_demo_image_set.py`
- Test: `tests/unit/test_demo_image_set_builder.py`

**Step 1: Write the failing test**

Create a unit test using `tmp_path` that builds a fake source image tree, runs the script entry point, and asserts:

- Up to the default limit of 24 images are copied
- A `manifest.json` file is written
- Relative paths are preserved in the output

```python
def test_build_demo_image_set_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "demo"
    # create sample images...

    exit_code = main(["--source", str(source), "--output", str(output)])

    assert exit_code == 0
    assert (output / "manifest.json").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_demo_image_set_builder.py -v`
Expected: FAIL because the script does not exist yet.

**Step 3: Write minimal implementation**

Implement a small CLI that:

- Walks a source directory for image files
- Sorts deterministically
- Copies at most the requested count
- Preserves relative paths
- Computes SHA-256 for each copied file
- Writes a JSON manifest

Keep the first version simple and deterministic. Do not overbuild sampling heuristics.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_demo_image_set_builder.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/build_demo_image_set.py tests/unit/test_demo_image_set_builder.py
git commit -m "feat: add demo image dataset builder"
```

### Task 5: Verify the whole workflow and document usage

**Files:**
- Modify: `tests/fixtures/README.md`
- Modify: `sample-data/README.md`
- Optional Modify: `README.md`

**Step 1: Write the failing test**

Add a lightweight docs assertion or extend an existing README test so the demo builder command is mentioned where appropriate.

```python
def test_sample_data_readme_mentions_builder() -> None:
    text = Path("sample-data/README.md").read_text()
    assert "build_demo_image_set.py" in text
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_readme.py -k sample_data_readme_mentions_builder -v`
Expected: FAIL until the docs are updated.

**Step 3: Write minimal implementation**

Document:

- Where fixture images live
- How to run the demo builder
- That generated demo data should not be committed

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_readme.py -k sample_data_readme_mentions_builder -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/README.md sample-data/README.md README.md tests/unit/test_readme.py
git commit -m "docs: describe image dataset workflow"
```
