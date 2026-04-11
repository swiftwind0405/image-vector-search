from pathlib import Path


def test_fixture_docs_exist() -> None:
    assert Path("tests/fixtures/README.md").exists()
    assert Path("sample-data/README.md").exists()


def test_sample_data_readme_mentions_builder() -> None:
    text = Path("sample-data/README.md").read_text(encoding="utf-8")
    assert "build_demo_image_set.py" in text


def test_readme_mentions_required_environment_variables():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "JINA_API_KEY" in readme
    assert "/data/images" in readme
    assert "/data/config" in readme
