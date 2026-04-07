from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.tagging import TagService
from image_vector_search.api.admin_bulk_routes import create_admin_bulk_router
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


@pytest.fixture
def app(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    # Seed 3 images in different folders
    repo.upsert_image(_make_image("aaa", "/data/images/nature/rose.jpg"))
    repo.upsert_image(_make_image("bbb", "/data/images/nature/tulip.jpg"))
    repo.upsert_image(_make_image("ccc", "/data/images/urban/city.jpg"))
    tag_service = TagService(repository=repo)
    app = FastAPI()
    app.include_router(create_admin_tag_router(tag_service=tag_service))
    app.include_router(
        create_admin_bulk_router(tag_service=tag_service, images_root="/data/images")
    )
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestFolderListing:
    @pytest.mark.anyio
    async def test_list_folders_returns_distinct_folders(self, client):
        resp = await client.get("/api/folders")
        assert resp.status_code == 200
        folders = resp.json()
        assert sorted(folders) == ["nature", "urban"]


class TestBulkTagsBySelection:
    @pytest.mark.anyio
    async def test_bulk_add_tags_returns_affected_count(self, client):
        # Create a tag first
        resp = await client.post("/api/tags", json={"name": "outdoor"})
        assert resp.status_code == 201
        tag_id = resp.json()["id"]

        resp = await client.post(
            "/api/bulk/tags/add",
            json={"content_hashes": ["aaa", "bbb"], "tag_id": tag_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_remove_tags_works(self, client):
        resp = await client.post("/api/tags", json={"name": "outdoor"})
        tag_id = resp.json()["id"]

        # Add tags first
        await client.post(
            "/api/bulk/tags/add",
            json={"content_hashes": ["aaa", "bbb", "ccc"], "tag_id": tag_id},
        )

        # Now remove from two
        resp = await client.post(
            "/api/bulk/tags/remove",
            json={"content_hashes": ["aaa", "bbb"], "tag_id": tag_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_add_categories_works(self, client):
        resp = await client.post("/api/categories", json={"name": "Nature"})
        assert resp.status_code == 201
        category_id = resp.json()["id"]

        resp = await client.post(
            "/api/bulk/categories/add",
            json={"content_hashes": ["aaa", "bbb"], "category_id": category_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["affected"] == 2

    @pytest.mark.anyio
    async def test_exceeding_500_hashes_returns_400(self, client):
        resp = await client.post("/api/tags", json={"name": "overflow"})
        tag_id = resp.json()["id"]

        hashes = [f"hash{i:04d}" for i in range(501)]
        resp = await client.post(
            "/api/bulk/tags/add",
            json={"content_hashes": hashes, "tag_id": tag_id},
        )
        assert resp.status_code == 400


class TestBulkTagsByFolder:
    @pytest.mark.anyio
    async def test_bulk_folder_add_tags_works(self, client):
        resp = await client.post("/api/tags", json={"name": "nature-tag"})
        tag_id = resp.json()["id"]

        resp = await client.post(
            "/api/bulk/folder/tags/add",
            json={"folder": "nature", "tag_id": tag_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        # 2 images in nature folder
        assert data["affected"] == 2

    @pytest.mark.anyio
    async def test_bulk_folder_remove_tags_works(self, client):
        resp = await client.post("/api/tags", json={"name": "nature-tag"})
        tag_id = resp.json()["id"]

        # Add first
        await client.post(
            "/api/bulk/folder/tags/add",
            json={"folder": "nature", "tag_id": tag_id},
        )

        # Now remove
        resp = await client.post(
            "/api/bulk/folder/tags/remove",
            json={"folder": "nature", "tag_id": tag_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["affected"] == 2


class TestFileOperations:
    @pytest.mark.anyio
    async def test_open_file_outside_root_returns_400(self, client):
        resp = await client.post(
            "/api/files/open",
            json={"path": "/etc/passwd"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_open_nonexistent_file_returns_404(self, client):
        resp = await client.post(
            "/api/files/open",
            json={"path": "/data/images/nature/nonexistent.jpg"},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_reveal_file_outside_root_returns_400(self, client):
        resp = await client.post(
            "/api/files/reveal",
            json={"path": "/tmp/evil.jpg"},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_reveal_nonexistent_file_returns_404(self, client):
        resp = await client.post(
            "/api/files/reveal",
            json={"path": "/data/images/urban/nonexistent.jpg"},
        )
        assert resp.status_code == 404
