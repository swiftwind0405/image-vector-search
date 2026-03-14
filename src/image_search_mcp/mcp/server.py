from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult


def build_mcp_server(search_service) -> FastMCP:
    mcp = FastMCP("image-search-mcp")

    @mcp.tool
    async def search_images(
        query: str,
        top_k: int = 5,
        min_score: float = 0.0,
        folder: str | None = None,
    ) -> ToolResult:
        results = await search_service.search_images(
            query=query,
            top_k=top_k,
            min_score=min_score,
            folder=folder,
        )
        return _tool_result(results)

    @mcp.tool
    async def search_similar(
        image_path: str,
        top_k: int = 5,
        min_score: float = 0.0,
        folder: str | None = None,
    ) -> ToolResult:
        results = await search_service.search_similar(
            image_path=image_path,
            top_k=top_k,
            min_score=min_score,
            folder=folder,
        )
        return _tool_result(results)

    return mcp


def _tool_result(results: list) -> ToolResult:
    payload = [
        result.model_dump() if hasattr(result, "model_dump") else dict(result)
        for result in results
    ]
    return ToolResult(content=[], structured_content={"results": payload})
