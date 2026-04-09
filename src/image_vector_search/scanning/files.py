import os
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


def iter_image_files(
    images_root: Path,
    excluded_folders: list[str] | None = None,
) -> Iterator[Path]:
    resolved_root = images_root.resolve()
    if not resolved_root.exists():
        return iter(())

    excluded_prefixes = _build_excluded_prefixes(resolved_root, excluded_folders)

    supported_paths = sorted(
        (
            path.resolve()
            for path in resolved_root.rglob("*")
            if path.is_file()
            and is_supported_image(path)
            and not _is_excluded(path.resolve(), excluded_prefixes)
        ),
        key=lambda path: path.as_posix(),
    )
    return iter(supported_paths)


def scan_disk_folders(images_root: Path) -> list[str]:
    """Return sorted list of all subdirectory relative paths found under *images_root*.

    Uses os.walk to iterate directories only, avoiding the O(total-files) cost
    of rglob("*") on large image libraries.
    """
    resolved_root = images_root.resolve()
    if not resolved_root.exists():
        return []

    folders: list[str] = []
    root_str = str(resolved_root)
    for dirpath, dirnames, _ in os.walk(root_str):
        for name in dirnames:
            full = Path(dirpath) / name
            try:
                relative = full.relative_to(resolved_root).as_posix()
            except ValueError:
                continue
            folders.append(relative)
    return sorted(folders)


def _build_excluded_prefixes(
    resolved_root: Path,
    excluded_folders: list[str] | None,
) -> list[str]:
    if not excluded_folders:
        return []
    return [
        (resolved_root / folder.strip("/")).as_posix() + "/"
        for folder in excluded_folders
        if folder.strip("/")
    ]


def _is_excluded(resolved_path: Path, excluded_prefixes: list[str]) -> bool:
    if not excluded_prefixes:
        return False
    path_str = resolved_path.as_posix() + "/"
    return any(path_str.startswith(prefix) for prefix in excluded_prefixes)


def to_container_path(path: Path, images_root: Path) -> str:
    resolved_root = images_root.resolve()
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Path must be inside images_root: {resolved_root}") from exc
    return resolved_path.as_posix()
