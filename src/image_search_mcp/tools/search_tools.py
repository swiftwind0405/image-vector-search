from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import registry


@registry.tool(
    name="search_images",
    description="Search images by text description using semantic similarity",
)
async def search_images(
    ctx: ToolContext,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0,
    folder: str | None = None,
) -> dict:
    results = await ctx.search_service.search_images(
        query=query,
        folder=folder,
        top_k=top_k,
        min_score=min_score,
    )
    return {"results": [result.model_dump() for result in results]}


@registry.tool(
    name="search_similar",
    description="Find images visually similar to a given image",
)
async def search_similar(
    ctx: ToolContext,
    image_path: str,
    top_k: int = 5,
    min_score: float = 0.0,
    folder: str | None = None,
) -> dict:
    results = await ctx.search_service.search_similar(
        image_path=image_path,
        folder=folder,
        top_k=top_k,
        min_score=min_score,
    )
    return {"results": [result.model_dump() for result in results]}
