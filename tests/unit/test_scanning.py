from pathlib import Path

import pytest
from PIL import Image

from image_vector_search.scanning.files import (
    iter_image_files,
    is_supported_image,
    scan_disk_folders,
    to_container_path,
)
from image_vector_search.scanning.hashing import sha256_file
from image_vector_search.scanning.image_metadata import read_image_metadata


def test_supported_image_extensions():
    assert is_supported_image(Path("a.jpg")) is True
    assert is_supported_image(Path("b.PNG")) is True
    assert is_supported_image(Path("c.webp")) is True
    assert is_supported_image(Path("d.txt")) is False


def test_iter_image_files_returns_sorted_supported_images(tmp_path: Path):
    images_root = tmp_path / "images"
    nested = images_root / "2024" / "vacation"
    nested.mkdir(parents=True)
    (nested / "b.png").write_bytes(b"png")
    (nested / "a.jpg").write_bytes(b"jpg")
    (nested / "notes.txt").write_text("ignore")

    results = list(iter_image_files(images_root))

    assert results == [nested / "a.jpg", nested / "b.png"]


def test_iter_image_files_skips_excluded_folders(tmp_path: Path):
    images_root = tmp_path / "images"
    keep = images_root / "keep"
    drop = images_root / "drop"
    nested_drop = images_root / "keep" / "private"
    keep.mkdir(parents=True)
    drop.mkdir(parents=True)
    nested_drop.mkdir(parents=True)
    (keep / "a.jpg").write_bytes(b"jpg")
    (drop / "b.jpg").write_bytes(b"jpg")
    (nested_drop / "c.jpg").write_bytes(b"jpg")

    results = list(
        iter_image_files(images_root, excluded_folders=["drop", "keep/private"])
    )

    assert results == [(keep / "a.jpg").resolve()]


def test_iter_image_files_excluded_prefix_does_not_match_sibling(tmp_path: Path):
    # "foo" must not accidentally exclude "foobar".
    images_root = tmp_path / "images"
    (images_root / "foo").mkdir(parents=True)
    (images_root / "foobar").mkdir(parents=True)
    (images_root / "foo" / "x.jpg").write_bytes(b"jpg")
    (images_root / "foobar" / "y.jpg").write_bytes(b"jpg")

    results = list(iter_image_files(images_root, excluded_folders=["foo"]))

    assert results == [(images_root / "foobar" / "y.jpg").resolve()]


def test_scan_disk_folders_returns_nested_relative_paths(tmp_path: Path):
    images_root = tmp_path / "images"
    (images_root / "a" / "b").mkdir(parents=True)
    (images_root / "c").mkdir(parents=True)

    folders = scan_disk_folders(images_root)

    assert folders == ["a", "a/b", "c"]


def test_scan_disk_folders_missing_root_returns_empty(tmp_path: Path):
    assert scan_disk_folders(tmp_path / "does-not-exist") == []


def test_sha256_file_is_stable(tmp_path: Path):
    sample = tmp_path / "a.txt"
    sample.write_text("abc")

    assert sha256_file(sample) == sha256_file(sample)


def test_read_image_metadata_returns_dimensions_and_mime_type(tmp_path: Path):
    image_path = tmp_path / "sample.png"
    Image.new("RGB", (12, 8), color="red").save(image_path)

    metadata = read_image_metadata(image_path)

    assert metadata.width == 12
    assert metadata.height == 8
    assert metadata.mime_type == "image/png"


def test_to_container_path_requires_path_under_images_root(tmp_path: Path):
    images_root = tmp_path / "images"
    images_root.mkdir()
    image_path = images_root / "2024" / "photo.jpg"
    image_path.parent.mkdir()
    image_path.write_bytes(b"jpg")

    assert to_container_path(image_path, images_root) == str(image_path.resolve())

    outside_path = tmp_path / "outside.jpg"
    outside_path.write_bytes(b"jpg")
    with pytest.raises(ValueError, match="images_root"):
        to_container_path(outside_path, images_root)
