from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Sequence


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
DEFAULT_LIMIT = 24


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_image_paths(source_root: Path) -> list[Path]:
    return sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def build_demo_image_set(source_root: Path, output_root: Path, limit: int = DEFAULT_LIMIT) -> dict:
    source_root = source_root.resolve()
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    images: list[dict[str, str | int]] = []
    for source_path in _iter_image_paths(source_root)[:limit]:
        relative_path = source_path.relative_to(source_root)
        target_path = output_root / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        images.append(
            {
                "relative_path": relative_path.as_posix(),
                "source_path": str(source_path),
                "output_path": str(target_path),
                "sha256": _sha256(target_path),
                "size_bytes": target_path.stat().st_size,
            }
        )

    manifest = {
        "source_root": str(source_root),
        "output_root": str(output_root),
        "copied_count": len(images),
        "limit": limit,
        "images": images,
    }
    (output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a small local demo image dataset.")
    parser.add_argument("--source", required=True, type=Path, help="Source image directory")
    parser.add_argument("--output", required=True, type=Path, help="Output demo dataset directory")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum number of images to copy (default: {DEFAULT_LIMIT})",
    )
    args = parser.parse_args(argv)

    build_demo_image_set(args.source, args.output, limit=args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
