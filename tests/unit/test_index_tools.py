from unittest.mock import MagicMock

import pytest

from image_vector_search.tools.context import ToolContext
from image_vector_search.tools.image_tools import get_image_info, list_images
from image_vector_search.tools.index_tools import get_index_status, trigger_index


class FakeStatusService:
    async def get_index_status(self):
        return MagicMock(
            model_dump=lambda: {
                "images_on_disk": 10,
                "total_images": 8,
                "active_images": 8,
            }
        )

    async def list_recent_jobs(self, limit=5):
        return []

    async def list_active_images_with_labels(self, folder=None, tag_id=None, category_id=None):
        images = [MagicMock(model_dump=lambda: {"content_hash": "abc", "path": "/a.jpg"})]
        if folder:
            return [item for item in images if folder in "/a.jpg"]
        return images

    async def get_image(self, content_hash):
        if content_hash == "unknown":
            return None
        return MagicMock(content_hash=content_hash, model_dump=lambda: {"content_hash": content_hash})

    async def list_tags_for_image(self, content_hash):
        return []

    async def list_categories_for_image(self, content_hash):
        return []


class FakeJobRunner:
    async def enqueue(self, mode):
        return MagicMock(id=1, mode=mode, model_dump=lambda: {"id": 1, "mode": mode})


@pytest.fixture
def ctx():
    return ToolContext(
        search_service=None,
        tag_service=None,
        status_service=FakeStatusService(),
        job_runner=FakeJobRunner(),
        settings=None,
    )


@pytest.mark.asyncio
async def test_get_index_status(ctx):
    result = await get_index_status(ctx)
    assert "status" in result
    assert "images_on_disk" in result["status"]


@pytest.mark.asyncio
async def test_trigger_index_incremental(ctx):
    result = await trigger_index(ctx, mode="incremental")
    assert "job" in result
    assert result["job"]["mode"] == "incremental"


@pytest.mark.asyncio
async def test_trigger_index_full_rebuild(ctx):
    result = await trigger_index(ctx, mode="full_rebuild")
    assert "job" in result


@pytest.mark.asyncio
async def test_list_images(ctx):
    result = await list_images(ctx)
    assert "images" in result
    assert len(result["images"]) >= 1


@pytest.mark.asyncio
async def test_list_images_with_folder(ctx):
    result = await list_images(ctx, folder="vacation")
    assert "images" in result


@pytest.mark.asyncio
async def test_get_image_info(ctx):
    result = await get_image_info(ctx, content_hash="abc")
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_get_image_info_not_found(ctx):
    with pytest.raises(ValueError):
        await get_image_info(ctx, content_hash="unknown")
