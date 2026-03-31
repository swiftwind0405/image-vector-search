from fastapi import FastAPI
from fastapi.testclient import TestClient

from image_search_mcp.adapters.http_tool_adapter import build_tool_router
from image_search_mcp.tools.context import ToolContext
from image_search_mcp.tools.registry import ToolRegistry


def make_test_app():
    reg = ToolRegistry()

    @reg.tool(name="search_images", description="Search images")
    async def search_images(ctx: ToolContext, query: str, top_k: int = 5) -> dict:
        return {"results": [{"path": "/img.jpg", "score": 0.9}]}

    @reg.tool(name="manage_tags", description="Manage tags")
    async def manage_tags(ctx: ToolContext, action: str, name: str = None) -> dict:
        if not name:
            raise ValueError("name is required")
        return {"tag": {"name": name}}

    @reg.tool(name="search_similar", description="Find similar")
    async def search_similar(ctx: ToolContext, image_path: str) -> dict:
        raise FileNotFoundError(f"Image not found: {image_path}")

    ctx = ToolContext(
        search_service=None,
        tag_service=None,
        status_service=None,
        job_runner=None,
        settings=None,
    )
    app = FastAPI()
    router = build_tool_router(reg, ctx)
    app.include_router(router)
    return app, reg


def test_discovery_endpoint():
    app, _ = make_test_app()
    client = TestClient(app)
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.json()
    assert isinstance(tools, list)
    assert len(tools) == 3
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool


def test_invoke_tool_success():
    app, _ = make_test_app()
    client = TestClient(app)
    resp = client.post("/api/tools/search_images", json={"query": "sunset", "top_k": 5})
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_invoke_nonexistent_tool():
    app, _ = make_test_app()
    client = TestClient(app)
    resp = client.post("/api/tools/nonexistent", json={})
    assert resp.status_code == 404
    assert "nonexistent" in resp.text


def test_invoke_tool_value_error():
    app, _ = make_test_app()
    client = TestClient(app)
    resp = client.post("/api/tools/manage_tags", json={"action": "create"})
    assert resp.status_code == 400
    assert "name is required" in resp.text


def test_invoke_tool_file_not_found():
    app, _ = make_test_app()
    client = TestClient(app)
    resp = client.post("/api/tools/search_similar", json={"image_path": "/nonexistent.jpg"})
    assert resp.status_code == 404
