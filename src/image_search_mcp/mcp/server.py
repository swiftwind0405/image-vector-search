from fastmcp import FastMCP

from image_search_mcp.adapters.mcp_adapter import build_mcp_from_registry
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolRegistry


def build_mcp_server(search_service) -> FastMCP:
    registry = ToolRegistry()

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
            top_k=top_k,
            min_score=min_score,
            folder=folder,
        )
        return {
            "results": [
                result.model_dump() if hasattr(result, "model_dump") else dict(result)
                for result in results
            ]
        }

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
            top_k=top_k,
            min_score=min_score,
            folder=folder,
        )
        return {
            "results": [
                result.model_dump() if hasattr(result, "model_dump") else dict(result)
                for result in results
            ]
        }

    ctx = ToolContext(
        search_service=search_service,
        tag_service=None,
        status_service=None,
        job_runner=None,
        settings=None,
    )
    return build_mcp_from_registry(registry, ctx)
