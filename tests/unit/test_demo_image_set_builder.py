import importlib.util
import json
from pathlib import Path

from PIL import Image


def _load_builder_module():
    script_path = Path("scripts/build_demo_image_set.py")
    spec = importlib.util.spec_from_file_location("build_demo_image_set", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_image(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (16, 12), color=color).save(path)


def test_build_demo_image_set_writes_manifest(tmp_path: Path) -> None:
    builder = _load_builder_module()
    source = tmp_path / "source"
    output = tmp_path / "demo"

    _create_image(source / "cats/orange.jpg", "orange")
    _create_image(source / "cats/blue.png", "blue")
    _create_image(source / "dogs/green.jpeg", "green")
    _create_image(source / "dogs/red.bmp", "red")

    exit_code = builder.main(["--source", str(source), "--output", str(output), "--limit", "3"])

    assert exit_code == 0
    assert (output / "cats/orange.jpg").exists()
    assert (output / "cats/blue.png").exists()
    assert (output / "dogs/green.jpeg").exists()
    assert not (output / "dogs/red.bmp").exists()

    manifest_path = output / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_root"] == str(source.resolve())
    assert manifest["output_root"] == str(output.resolve())
    assert manifest["copied_count"] == 3
    assert [item["relative_path"] for item in manifest["images"]] == [
        "cats/blue.png",
        "cats/orange.jpg",
        "dogs/green.jpeg",
    ]
    assert all("sha256" in item for item in manifest["images"])
