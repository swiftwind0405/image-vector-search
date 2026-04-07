import hashlib
from pathlib import Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_auto_fixture_images_exist() -> None:
    root = Path("tests/fixtures/images/auto")
    expected_paths = [
        "red-square.png",
        "orange-wide.jpg",
        "blue-tall.png",
        "green-small.jpg",
        "dup/content-same-orange-a.jpg",
        "dup/content-same-orange-b.jpg",
        "renamed/before/orange.jpg",
        "renamed/after/orange-renamed.jpg",
        "folders/2024/travel/red sunset.jpg",
        "folders/2024/人物/blue-portrait.png",
        "folders/misc/green_leaf.JPG",
        "variants/orange-border.png",
    ]

    for relative_path in expected_paths:
        assert (root / relative_path).exists(), relative_path


def test_duplicate_fixture_pairs_share_hash() -> None:
    root = Path("tests/fixtures/images/auto")
    assert _sha256(root / "dup/content-same-orange-a.jpg") == _sha256(
        root / "dup/content-same-orange-b.jpg"
    )


def test_renamed_fixture_pairs_share_hash() -> None:
    root = Path("tests/fixtures/images/auto")
    assert _sha256(root / "renamed/before/orange.jpg") == _sha256(
        root / "renamed/after/orange-renamed.jpg"
    )
