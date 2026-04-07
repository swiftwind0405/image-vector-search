from pathlib import Path
import tomllib


def test_pyproject_configures_src_layout_and_frontend_assets():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert pyproject["tool"]["setuptools"]["package-dir"] == {"": "src"}
    assert pyproject["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]

    package_data = pyproject["tool"]["setuptools"]["package-data"]["image_vector_search"]
    assert "frontend/dist/**" in package_data
