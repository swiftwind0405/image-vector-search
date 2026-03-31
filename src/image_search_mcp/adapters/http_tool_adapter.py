import logging

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


def build_tool_router(registry: ToolRegistry, ctx: ToolContext) -> APIRouter:
    router = APIRouter(prefix="/api/tools", tags=["tools"])

    @router.get("")
    async def discover_tools(response: Response):
        response.headers["Cache-Control"] = "public, max-age=3600"
        return [
            {
                "name": tool_def.name,
                "description": tool_def.description,
                "parameters": tool_def.input_schema,
            }
            for tool_def in registry.get_tools()
        ]

    @router.post("/{tool_name}")
    async def invoke_tool(tool_name: str, request: Request):
        tool_def = registry.get_tool(tool_name)
        if tool_def is None:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        try:
            result = await tool_def.fn(ctx, **payload)
            return JSONResponse(content=jsonable_encoder(result))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except Exception as exc:
            logger.exception("Tool %s raised unexpected error", tool_name)
            raise HTTPException(status_code=500, detail=str(exc))

    return router
