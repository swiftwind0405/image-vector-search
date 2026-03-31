from unittest.mock import MagicMock

import pytest

from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.search_tools import search_images, search_similar


class FakeSearchService:
    async def search_images(self, query, folder=None, top_k=5, min_score=0.0):
        return [
            MagicMock(
                model_dump=lambda: {
                    "content_hash": "abc",
                    "path": "/img.jpg",
                    "score": 0.9,
                    "width": 100,
                    "height": 100,
                    "mime_type": "image/jpeg",
                }
            )
        ]

    async def search_similar(self, image_path, folder=None, top_k=5, min_score=0.0):
        return [
            MagicMock(
                model_dump=lambda: {
                    "content_hash": "def",
                    "path": "/img2.jpg",
                    "score": 0.8,
                    "width": 200,
                    "height": 200,
                    "mime_type": "image/jpeg",
                }
            )
        ]


@pytest.fixture
def ctx():
    settings = MagicMock()
    settings.images_root = "/images"
    return ToolContext(
        search_service=FakeSearchService(),
        tag_service=None,
        status_service=None,
        job_runner=None,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_search_images_tool(ctx):
    result = await search_images(ctx, query="sunset", top_k=3)
    assert "results" in result
    assert len(result["results"]) >= 1
    record = result["results"][0]
    assert "content_hash" in record
    assert "path" in record
    assert "score" in record


@pytest.mark.asyncio
async def test_search_similar_tool(ctx):
    result = await search_similar(ctx, image_path="/images/test.jpg", top_k=2)
    assert "results" in result
    assert len(result["results"]) >= 1
