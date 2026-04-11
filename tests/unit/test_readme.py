from pathlib import Path


def test_fixture_docs_exist() -> None:
    assert Path("tests/fixtures/README.md").exists()


def test_fixture_readme_mentions_demo_builder() -> None:
    text = Path("tests/fixtures/README.md").read_text(encoding="utf-8")
    assert "build_demo_image_set.py" in text
    assert "tmp/demo-set" in text


def test_readme_mentions_required_environment_variables():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "JINA_API_KEY" in readme
    assert "/data/images" in readme
    assert "/data/config" in readme


def test_readme_mentions_make_dev() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "make dev" in readme
    assert "make dev-backend" in readme
    assert "make dev-frontend" in readme
