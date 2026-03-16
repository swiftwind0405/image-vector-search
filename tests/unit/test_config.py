import os
from pathlib import Path

from image_search_mcp.config import Settings


def test_settings_defaults(monkeypatch):
    # Clear environment variables that would override defaults
    for key in list(os.environ.keys()):
        if key.startswith("IMAGE_SEARCH_"):
            monkeypatch.delenv(key, raising=False)
    settings = Settings()
    assert settings.images_root == Path("/data/images")
    assert settings.index_root == Path("/data/index")
    assert settings.default_top_k == 5
    assert settings.max_top_k == 50
