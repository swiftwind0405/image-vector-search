from pathlib import Path

from image_search_mcp.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.images_root == Path("/data/images")
    assert settings.index_root == Path("/data/index")
    assert settings.default_top_k == 5
    assert settings.max_top_k == 50
