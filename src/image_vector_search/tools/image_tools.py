from image_vector_search.tools._helpers import maybe_await
from image_vector_search.tools.context import ToolContext
from image_vector_search.tools.registry import registry


@registry.tool(
    name="list_images",
    description="List indexed images with optional folder/tag filter",
)
async def list_images(
    ctx: ToolContext,
    folder: str | None = None,
    tag_id: int | None = None,
) -> dict:
    images = await maybe_await(
        ctx.status_service.list_active_images_with_labels(
            folder=folder,
            tag_id=tag_id,
        )
    )
    return {"images": [image.model_dump() for image in images]}


@registry.tool(
    name="get_image_info",
    description="Get metadata and tags for a specific image",
)
async def get_image_info(ctx: ToolContext, content_hash: str) -> dict:
    image = await maybe_await(ctx.status_service.get_image(content_hash))
    if image is None:
        raise ValueError(f"Image not found: {content_hash}")

    result = image.model_dump()

    try:
        if hasattr(ctx.status_service, "list_tags_for_image"):
            tags = await maybe_await(ctx.status_service.list_tags_for_image(content_hash))
        else:
            tags = await maybe_await(ctx.tag_service.get_image_tags(content_hash))
        result["tags"] = [tag.model_dump() if hasattr(tag, "model_dump") else tag for tag in tags]
    except Exception:
        result["tags"] = []

    return result
