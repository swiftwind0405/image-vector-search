from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.status import StatusService
from image_vector_search.services.tagging import TagService
from image_vector_search.api.admin_routes import create_admin_router
from image_vector_search.api.admin_tag_routes import create_admin_tag_router

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_image(content_hash: str, canonical_path: str) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=True,
        last_seen_at=NOW,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=NOW,
        updated_at=NOW,
    )


class DummyVectorIndex:
    def count(self, _: str) -> int:
        return 0


class DummyJobRunner:
    def enqueue(self, job_type: str):
        return {"id": f"job-{job_type}"}


class DummySearchService:
    async def search_images(self, **kwargs):
        return []

    async def search_similar(self, **kwargs):
        return []


class DummySettings:
    def __init__(self, images_root: Path) -> None:
        self.images_root = images_root
        self.embedding_provider = "jina"
        self.embedding_model = "jina-clip-v2"
        self.embedding_version = "v2"


@pytest.fixture
def app(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    images_root = tmp_path / "images"
    images_root.mkdir()

    repo.upsert_image(_make_image("aaa", str(images_root / "nature" / "rose.jpg")))
    repo.upsert_image(_make_image("bbb", str(images_root / "nature" / "tulip.jpg")))
    repo.upsert_image(_make_image("ccc", str(images_root / "urban" / "city.jpg")))

    tag_service = TagService(repository=repo)
    status_service = StatusService(
        settings=DummySettings(images_root),
        repository=repo,
        vector_index=DummyVectorIndex(),
    )

    app = FastAPI()
    app.include_router(create_admin_tag_router(tag_service=tag_service))
    app.include_router(
        create_admin_router(
            status_service=status_service,
            job_runner=DummyJobRunner(),
            search_service=DummySearchService(),
        )
    )
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


class TestFilteredImagesAPI:
    @pytest.mark.anyio
    async def test_list_images_filtered_by_tag(self, client):
        tag_id = (await client.post("/api/tags", json={"name": "flower"})).json()["id"]
        await client.post("/api/images/aaa/tags", json={"tag_id": tag_id})
        await client.post("/api/images/bbb/tags", json={"tag_id": tag_id})

        response = await client.get(f"/api/images?tag_id={tag_id}")

        assert response.status_code == 200
        assert [image["content_hash"] for image in response.json()["items"]] == ["aaa", "bbb"]

    @pytest.mark.anyio
    async def test_list_images_filtered_by_category_includes_descendants(self, client):
        parent_id = (await client.post("/api/categories", json={"name": "Nature"})).json()["id"]
        child_id = (
            await client.post("/api/categories", json={"name": "Flowers", "parent_id": parent_id})
        ).json()["id"]
        await client.post("/api/images/aaa/categories", json={"category_id": parent_id})
        await client.post("/api/images/bbb/categories", json={"category_id": child_id})

        response = await client.get(f"/api/images?category_id={parent_id}")

        assert response.status_code == 200
        assert [image["content_hash"] for image in response.json()["items"]] == ["aaa", "bbb"]

    @pytest.mark.anyio
    async def test_list_images_filtered_by_category_can_exclude_descendants(self, client):
        parent_id = (await client.post("/api/categories", json={"name": "Nature"})).json()["id"]
        child_id = (
            await client.post("/api/categories", json={"name": "Flowers", "parent_id": parent_id})
        ).json()["id"]
        await client.post("/api/images/aaa/categories", json={"category_id": parent_id})
        await client.post("/api/images/bbb/categories", json={"category_id": child_id})

        response = await client.get(
            f"/api/images?category_id={parent_id}&include_descendants=false"
        )

        assert response.status_code == 200
        assert [image["content_hash"] for image in response.json()["items"]] == ["aaa"]

    @pytest.mark.anyio
    async def test_list_images_composes_tag_and_folder_filters(self, client):
        tag_id = (await client.post("/api/tags", json={"name": "featured"})).json()["id"]
        await client.post("/api/images/aaa/tags", json={"tag_id": tag_id})
        await client.post("/api/images/ccc/tags", json={"tag_id": tag_id})

        response = await client.get(f"/api/images?tag_id={tag_id}&folder=nature")

        assert response.status_code == 200
        assert [image["content_hash"] for image in response.json()["items"]] == ["aaa"]
