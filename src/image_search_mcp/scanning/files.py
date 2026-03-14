from collections.abc import Iterator
from pathlib import Path


SUPPORTED_IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tiff",
    ".webp",
}


def is_supported_image(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def iter_image_files(images_root: Path) -> Iterator[Path]:
    resolved_root = images_root.resolve()
    if not resolved_root.exists():
        return iter(())

    supported_paths = sorted(
        (path.resolve() for path in resolved_root.rglob("*") if path.is_file() and is_supported_image(path)),
        key=lambda path: path.as_posix(),
    )
    return iter(supported_paths)


def to_container_path(path: Path, images_root: Path) -> str:
    resolved_root = images_root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path must be inside images_root: {resolved_root}") from exc
    return resolved_path.as_posix()
