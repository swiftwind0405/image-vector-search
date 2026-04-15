from typing import Literal

from image_vector_search.tools._helpers import maybe_await
from image_vector_search.tools.context import ToolContext
from image_vector_search.tools.registry import registry


@registry.tool(
    name="manage_tags",
    description="Create, rename, delete, or list image tags",
)
async def manage_tags(
    ctx: ToolContext,
    action: Literal["create", "rename", "delete", "list"],
    name: str | None = None,
    tag_id: int | None = None,
    new_name: str | None = None,
) -> dict:
    svc = ctx.tag_service
    if action == "create":
        if not name:
            raise ValueError("name is required for action=create")
        tag = await maybe_await(svc.create_tag(name))
        return {"tag": tag.model_dump()}
    if action == "list":
        tags = await maybe_await(svc.list_tags())
        return {"tags": [tag.model_dump() for tag in tags]}
    if action == "rename":
        if tag_id is None or not new_name:
            raise ValueError("tag_id and new_name required for action=rename")
        renamed = await maybe_await(svc.rename_tag(tag_id, new_name))
        if renamed is None:
            renamed = {"id": tag_id, "name": new_name}
            return {"tag": renamed}
        return {"tag": renamed.model_dump() if hasattr(renamed, "model_dump") else renamed}
    if action == "delete":
        if tag_id is None:
            raise ValueError("tag_id required for action=delete")
        await maybe_await(svc.delete_tag(tag_id))
        return {"deleted": tag_id}
    raise ValueError(f"Unknown action: {action}")


@registry.tool(
    name="tag_images",
    description="Add or remove tags from images",
)
async def tag_images(
    ctx: ToolContext,
    action: Literal["add_tag", "remove_tag", "list_tags"],
    content_hash: str,
    tag_id: int | None = None,
) -> dict:
    svc = ctx.tag_service
    if action == "add_tag":
        await maybe_await(svc.add_tag_to_image(content_hash, tag_id))
        return {"ok": True}
    if action == "remove_tag":
        await maybe_await(svc.remove_tag_from_image(content_hash, tag_id))
        return {"ok": True}
    if action == "list_tags":
        list_tags = getattr(svc, "list_tags_for_image", None) or getattr(svc, "get_image_tags")
        tags = await maybe_await(list_tags(content_hash))
        return {
            "tags": [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in tags]
            if tags
            else []
        }
    raise ValueError(f"Unknown action: {action}")
