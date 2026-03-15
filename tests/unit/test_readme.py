from pathlib import Path


def test_readme_mentions_required_environment_variables():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "JINA_API_KEY" in readme
    assert "/data/images" in readme
    assert "/data/index" in readme
