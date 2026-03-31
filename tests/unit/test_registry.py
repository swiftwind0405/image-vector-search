import pytest
from typing import Literal

from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolDef, ToolRegistry


def test_register_tool_via_decorator():
    reg = ToolRegistry()

    @reg.tool(name="my_tool", description="Does things")
    async def my_tool(ctx: ToolContext, x: str):
        return None

    assert "my_tool" in [t.name for t in reg.get_tools()]
    td = reg.get_tool("my_tool")
    assert td.description == "Does things"
    assert td.fn is my_tool


def test_infer_schema_from_type_hints():
    reg = ToolRegistry()

    @reg.tool(name="t", description="d")
    async def t(
        ctx: ToolContext,
        query: str,
        top_k: int = 5,
        folder: str | None = None,
    ):
        return None

    schema = reg.get_tool("t").input_schema
    assert schema["properties"]["query"]["type"] == "string"
    assert "query" in schema.get("required", [])
    assert schema["properties"]["top_k"]["type"] == "integer"
    assert schema["properties"]["top_k"].get("default") == 5
    assert "folder" not in schema.get("required", [])


def test_infer_literal_enum_schema():
    reg = ToolRegistry()

    @reg.tool(name="t", description="d")
    async def t(ctx: ToolContext, action: Literal["create", "delete", "list"]):
        return None

    schema = reg.get_tool("t").input_schema
    assert schema["properties"]["action"]["enum"] == ["create", "delete", "list"]


def test_exclude_tool_context_from_schema():
    reg = ToolRegistry()

    @reg.tool(name="t", description="d")
    async def t(ctx: ToolContext, x: str):
        return None

    schema = reg.get_tool("t").input_schema
    assert "ctx" not in schema.get("properties", {})


def test_list_all_tools():
    reg = ToolRegistry()
    for name in ["search_images", "manage_tags", "get_index_status"]:

        @reg.tool(name=name, description=f"{name} desc")
        async def fn(ctx: ToolContext):
            return None

    tools = reg.get_tools()
    assert len(tools) == 3
    for tool_def in tools:
        assert hasattr(tool_def, "name")
        assert hasattr(tool_def, "description")
        assert hasattr(tool_def, "fn")
        assert hasattr(tool_def, "input_schema")


def test_get_tool_by_name():
    reg = ToolRegistry()

    @reg.tool(name="search_images", description="search")
    async def fn(ctx: ToolContext):
        return None

    assert reg.get_tool("search_images") is not None
    assert reg.get_tool("nonexistent") is None
