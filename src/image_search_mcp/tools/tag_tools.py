from typing import Literal

from image_search_mcp.tools._helpers import maybe_await
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import registry


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
    name="manage_categories",
    description="Create, rename, delete, move, or list image categories",
)
async def manage_categories(
    ctx: ToolContext,
    action: Literal["create", "rename", "delete", "move", "list"],
    name: str | None = None,
    category_id: int | None = None,
    new_name: str | None = None,
    parent_id: int | None = None,
) -> dict:
    svc = ctx.tag_service
    if action == "create":
        if not name:
            raise ValueError("name is required for action=create")
        category = await maybe_await(svc.create_category(name, parent_id=parent_id))
        return {"category": category.model_dump()}
    if action == "list":
        categories = await maybe_await(svc.get_category_tree())
        return {
            "categories": [
                category.model_dump() if hasattr(category, "model_dump") else category
                for category in categories
            ]
        }
    if action == "rename":
        if category_id is None or not new_name:
            raise ValueError("category_id and new_name required for action=rename")
        renamed = await maybe_await(svc.rename_category(category_id, new_name))
        if renamed is None:
            renamed = {"id": category_id, "name": new_name}
            return {"category": renamed}
        return {
            "category": renamed.model_dump() if hasattr(renamed, "model_dump") else renamed
        }
    if action == "delete":
        if category_id is None:
            raise ValueError("category_id required for action=delete")
        await maybe_await(svc.delete_category(category_id))
        return {"deleted": category_id}
    if action == "move":
        if category_id is None:
            raise ValueError("category_id required for action=move")
        await maybe_await(svc.move_category(category_id, parent_id))
        return {"moved": category_id}
    raise ValueError(f"Unknown action: {action}")


@registry.tool(
    name="tag_images",
    description="Add or remove tags/categories from images",
)
async def tag_images(
    ctx: ToolContext,
    action: Literal[
        "add_tag",
        "remove_tag",
        "add_category",
        "remove_category",
        "list_tags",
        "list_categories",
    ],
    content_hash: str,
    tag_id: int | None = None,
    category_id: int | None = None,
) -> dict:
    svc = ctx.tag_service
    if action == "add_tag":
        await maybe_await(svc.add_tag_to_image(content_hash, tag_id))
        return {"ok": True}
    if action == "remove_tag":
        await maybe_await(svc.remove_tag_from_image(content_hash, tag_id))
        return {"ok": True}
    if action == "add_category":
        add_category = getattr(svc, "add_category_to_image", None) or getattr(
            svc, "add_image_to_category"
        )
        await maybe_await(add_category(content_hash, category_id))
        return {"ok": True}
    if action == "remove_category":
        remove_category = getattr(svc, "remove_category_from_image", None) or getattr(
            svc, "remove_image_from_category"
        )
        await maybe_await(remove_category(content_hash, category_id))
        return {"ok": True}
    if action == "list_tags":
        list_tags = getattr(svc, "list_tags_for_image", None) or getattr(svc, "get_image_tags")
        tags = await maybe_await(list_tags(content_hash))
        return {
            "tags": [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in tags]
            if tags
            else []
        }
    if action == "list_categories":
        list_categories = getattr(svc, "list_categories_for_image", None) or getattr(
            svc, "get_image_categories"
        )
        categories = await maybe_await(list_categories(content_hash))
        return {
            "categories": [
                category.model_dump() if hasattr(category, "model_dump") else category
                for category in categories
            ]
            if categories
            else []
        }
    raise ValueError(f"Unknown action: {action}")
