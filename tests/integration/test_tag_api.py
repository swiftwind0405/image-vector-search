import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.services.tagging import TagService
from image_search_mcp.web.tag_routes import create_tag_router


@pytest.fixture
def app(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    tag_service = TagService(repository=repo)
    app = FastAPI()
    app.include_router(create_tag_router(tag_service=tag_service))
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestTagAPI:
    @pytest.mark.anyio
    async def test_create_and_list_tags(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "sunset"
        resp = await client.get("/api/tags")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.anyio
    async def test_rename_tag(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = resp.json()["id"]
        resp = await client.put(f"/api/tags/{tag_id}", json={"name": "sunrise"})
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_delete_tag(self, client):
        resp = await client.post("/api/tags", json={"name": "sunset"})
        tag_id = resp.json()["id"]
        resp = await client.delete(f"/api/tags/{tag_id}")
        assert resp.status_code == 204


class TestCategoryAPI:
    @pytest.mark.anyio
    async def test_create_and_get_tree(self, client):
        resp = await client.post("/api/categories", json={"name": "Nature"})
        assert resp.status_code == 201
        parent_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "Flowers", "parent_id": parent_id})
        assert resp.status_code == 201
        resp = await client.get("/api/categories")
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) == 1
        assert len(tree[0]["children"]) == 1

    @pytest.mark.anyio
    async def test_delete_category(self, client):
        resp = await client.post("/api/categories", json={"name": "Nature"})
        cat_id = resp.json()["id"]
        resp = await client.delete(f"/api/categories/{cat_id}")
        assert resp.status_code == 204

    @pytest.mark.anyio
    async def test_move_category_to_root(self, client):
        resp = await client.post("/api/categories", json={"name": "Parent"})
        parent_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "Child", "parent_id": parent_id})
        child_id = resp.json()["id"]
        resp = await client.put(f"/api/categories/{child_id}", json={"move_to_root": True})
        assert resp.status_code == 200
        resp = await client.get("/api/categories")
        tree = resp.json()
        root_names = {n["name"] for n in tree}
        assert "Child" in root_names

    @pytest.mark.anyio
    async def test_move_category_to_new_parent(self, client):
        resp = await client.post("/api/categories", json={"name": "A"})
        a_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "B"})
        b_id = resp.json()["id"]
        resp = await client.post("/api/categories", json={"name": "Child", "parent_id": a_id})
        child_id = resp.json()["id"]
        resp = await client.put(f"/api/categories/{child_id}", json={"move_to_parent_id": b_id})
        assert resp.status_code == 200
        resp = await client.get(f"/api/categories/{b_id}/children")
        children = resp.json()
        assert len(children) == 1
        assert children[0]["name"] == "Child"
