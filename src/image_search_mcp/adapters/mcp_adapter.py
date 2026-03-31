from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from types import MethodType, SimpleNamespace

from fastmcp import Client, FastMCP
from fastmcp.tools import Tool

from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolDef, ToolRegistry


def build_mcp_from_registry(registry: ToolRegistry, ctx: ToolContext) -> FastMCP:
    mcp = FastMCP("image-search")

    def _make_handler(tool_def: ToolDef):
        async def handler(**kwargs):
            return await tool_def.fn(ctx, **kwargs)

        original_signature = inspect.signature(tool_def.fn)
        params = list(original_signature.parameters.values())
        if params and params[0].name == "ctx":
            params = params[1:]

        handler.__name__ = tool_def.name
        handler.__qualname__ = tool_def.name
        handler.__doc__ = tool_def.description
        handler.__signature__ = original_signature.replace(parameters=params)
        handler.__annotations__ = {
            key: value
            for key, value in getattr(tool_def.fn, "__annotations__", {}).items()
            if key != "ctx"
        }
        return handler

    for tool_def in registry.get_tools():
        wrapper = _make_handler(tool_def)
        mcp.add_tool(Tool.from_function(wrapper, name=tool_def.name, description=tool_def.description))

    async def get_tools(self):
        base_tools = await self.list_tools()
        wrapped_tools = []
        for tool in base_tools:
            tool_def = registry.get_tool(tool.name)
            wrapped_tools.append(
                SimpleNamespace(
                    name=tool.name,
                    description=getattr(tool, "description", None) or tool_def.description,
                    inputSchema=tool_def.input_schema,
                )
            )
        return wrapped_tools

    @asynccontextmanager
    async def test_client(self):
        async with Client(self) as client:
            yield _RegistryTestClient(client)

    mcp.get_tools = MethodType(get_tools, mcp)
    mcp.test_client = MethodType(test_client, mcp)
    return mcp


class _RegistryTestClient:
    def __init__(self, client: Client) -> None:
        self._client = client

    async def call_tool(self, name: str, arguments: dict):
        try:
            return await self._client.call_tool(name, arguments)
        except Exception as exc:
            return SimpleNamespace(isError=True, error=str(exc))
