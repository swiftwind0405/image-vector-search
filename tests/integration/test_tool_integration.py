import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_http_tool_discovery(app_bundle):
    transport = ASGITransport(app=app_bundle.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.json()
    tool_names = [tool["name"] for tool in tools]
    for expected in [
        "search_images",
        "search_similar",
        "manage_tags",
        "tag_images",
        "list_images",
        "get_image_info",
        "get_index_status",
        "trigger_index",
    ]:
        assert expected in tool_names, f"Missing tool: {expected}"


@pytest.mark.asyncio
async def test_http_trigger_index(app_bundle):
    transport = ASGITransport(app=app_bundle.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/tools/trigger_index", json={"mode": "incremental"})
    assert resp.status_code == 200
    assert "job" in resp.json()


@pytest.mark.asyncio
async def test_http_get_index_status(app_bundle):
    transport = ASGITransport(app=app_bundle.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/tools/get_index_status", json={})
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_http_manage_tags_roundtrip(app_bundle):
    transport = ASGITransport(app=app_bundle.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/tools/manage_tags",
            json={"action": "create", "name": "integration-test-tag"},
        )
        assert create_resp.status_code == 200
        tag_id = create_resp.json()["tag"]["id"]
        assert tag_id is not None

        list_resp = await client.post("/api/tools/manage_tags", json={"action": "list"})
        assert list_resp.status_code == 200
        names = [tag["name"] for tag in list_resp.json()["tags"]]
        assert "integration-test-tag" in names
