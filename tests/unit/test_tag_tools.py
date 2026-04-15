from unittest.mock import MagicMock

import pytest

from image_vector_search.tools.context import ToolContext
from image_vector_search.tools.tag_tools import manage_tags, tag_images


class FakeTagService:
    def __init__(self):
        self._tags = {}
        self._next_id = 1

    async def create_tag(self, name):
        tag = MagicMock(
            id=self._next_id,
            name=name,
            model_dump=lambda: {"id": self._next_id, "name": name},
        )
        self._tags[self._next_id] = tag
        self._next_id += 1
        return tag

    async def list_tags(self):
        return list(self._tags.values())

    async def rename_tag(self, tag_id, new_name):
        return MagicMock(
            id=tag_id,
            name=new_name,
            model_dump=lambda: {"id": tag_id, "name": new_name},
        )

    async def delete_tag(self, tag_id):
        return True

    async def add_tag_to_image(self, content_hash, tag_id):
        return True

    async def remove_tag_from_image(self, content_hash, tag_id):
        return True

    async def list_tags_for_image(self, content_hash):
        return []


@pytest.fixture
def ctx():
    return ToolContext(
        search_service=None,
        tag_service=FakeTagService(),
        status_service=None,
        job_runner=None,
        settings=None,
    )


@pytest.mark.asyncio
async def test_manage_tags_create(ctx):
    result = await manage_tags(ctx, action="create", name="landscape")
    assert "tag" in result
    assert result["tag"]["name"] == "landscape"


@pytest.mark.asyncio
async def test_manage_tags_list(ctx):
    await ctx.tag_service.create_tag("a")
    await ctx.tag_service.create_tag("b")
    result = await manage_tags(ctx, action="list")
    assert "tags" in result
    assert len(result["tags"]) >= 2


@pytest.mark.asyncio
async def test_manage_tags_rename(ctx):
    result = await manage_tags(ctx, action="rename", tag_id=1, new_name="renamed")
    assert "tag" in result


@pytest.mark.asyncio
async def test_manage_tags_delete(ctx):
    result = await manage_tags(ctx, action="delete", tag_id=1)
    assert "ok" in result or "deleted" in result


@pytest.mark.asyncio
async def test_manage_tags_missing_name(ctx):
    with pytest.raises(ValueError, match="name"):
        await manage_tags(ctx, action="create")


@pytest.mark.asyncio
async def test_manage_tags_empty_name(ctx):
    with pytest.raises(ValueError):
        await manage_tags(ctx, action="create", name="")


@pytest.mark.asyncio
async def test_tag_images_add(ctx):
    result = await tag_images(ctx, action="add_tag", content_hash="abc123", tag_id=1)
    assert result is not None


@pytest.mark.asyncio
async def test_tag_images_remove(ctx):
    result = await tag_images(ctx, action="remove_tag", content_hash="abc123", tag_id=1)
    assert result is not None
