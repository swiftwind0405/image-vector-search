from typing import Literal

import pytest

from image_search_mcp.adapters.mcp_adapter import build_mcp_from_registry
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolRegistry


def make_test_registry():
    reg = ToolRegistry()

    @reg.tool(name="echo_tool", description="Echoes input")
    async def echo_tool(ctx: ToolContext, message: str) -> dict:
        return {"echo": message}

    @reg.tool(name="error_tool", description="Raises error")
    async def error_tool(ctx: ToolContext, trigger: str) -> dict:
        raise ValueError("Invalid tag name")

    return reg


@pytest.fixture
def ctx():
    return ToolContext(
        search_service=None,
        tag_service=None,
        status_service=None,
        job_runner=None,
        settings=None,
    )


@pytest.mark.asyncio
async def test_build_mcp_server_tool_count(ctx):
    reg = make_test_registry()
    mcp = build_mcp_from_registry(reg, ctx)
    tools = await mcp.get_tools()
    assert len(tools) == 2


@pytest.mark.asyncio
async def test_mcp_tool_invocation(ctx):
    reg = make_test_registry()
    mcp = build_mcp_from_registry(reg, ctx)
    async with mcp.test_client() as client:
        result = await client.call_tool("echo_tool", {"message": "hello"})
        assert result is not None


@pytest.mark.asyncio
async def test_mcp_tool_error_handling(ctx):
    reg = make_test_registry()
    mcp = build_mcp_from_registry(reg, ctx)
    async with mcp.test_client() as client:
        result = await client.call_tool("error_tool", {"trigger": "go"})
        assert result.isError is True


@pytest.mark.asyncio
async def test_mcp_tool_schema_enum(ctx):
    reg = ToolRegistry()

    @reg.tool(name="manage_tags", description="Manage tags")
    async def manage_tags(ctx: ToolContext, action: Literal["create", "delete", "list"]):
        return None

    mcp = build_mcp_from_registry(reg, ctx)
    tools = await mcp.get_tools()
    tag_tool = next(tool for tool in tools if tool.name == "manage_tags")
    schema = tag_tool.inputSchema
    assert schema["properties"]["action"]["enum"] == ["create", "delete", "list"]
