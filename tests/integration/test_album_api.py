from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from image_vector_search.api.admin_album_routes import create_admin_album_router
from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.albums import AlbumService

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
        embedding_status="embedded",
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def app(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    images_root = tmp_path / "images"
    images_root.mkdir()
    for name in ["hash1", "hash2", "hash3"]:
        repo.upsert_image(_make_image(name, str(images_root / f"{name}.jpg")))
    tag_id = repo.create_tag("sunset").id
    repo.add_tag_to_image("hash1", tag_id)
    repo.add_tag_to_image("hash2", tag_id)

    album_service = AlbumService(repository=repo)

    app = FastAPI()
    app.include_router(create_admin_album_router(album_service=album_service))
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestAlbumApi:
    @pytest.mark.anyio
    async def test_create_manual_album(self, client):
        response = await client.post("/api/albums", json={"name": "Vacation", "type": "manual"})
        assert response.status_code == 201
        assert response.json()["name"] == "Vacation"

    @pytest.mark.anyio
    async def test_create_smart_album(self, client):
        response = await client.post(
            "/api/albums",
            json={"name": "Sunsets", "type": "smart", "rule_logic": "and"},
        )
        assert response.status_code == 201

    @pytest.mark.anyio
    async def test_album_name_must_be_unique(self, client):
        await client.post("/api/albums", json={"name": "My Album", "type": "manual"})
        response = await client.post("/api/albums", json={"name": "My Album", "type": "manual"})
        assert response.status_code == 409

    @pytest.mark.anyio
    async def test_album_name_must_not_be_empty(self, client):
        response = await client.post("/api/albums", json={"name": "", "type": "manual"})
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_list_all_albums(self, client):
        await client.post("/api/albums", json={"name": "A", "type": "manual"})
        await client.post("/api/albums", json={"name": "B", "type": "smart", "rule_logic": "or"})
        await client.post("/api/albums", json={"name": "C", "type": "manual"})
        response = await client.get("/api/albums")
        assert response.status_code == 200
        assert len(response.json()) == 3

    @pytest.mark.anyio
    async def test_get_album_detail(self, client):
        created = await client.post("/api/albums", json={"name": "Detail", "type": "manual"})
        album_id = created.json()["id"]
        response = await client.get(f"/api/albums/{album_id}")
        assert response.status_code == 200
        assert response.json()["id"] == album_id

    @pytest.mark.anyio
    async def test_get_nonexistent_album_returns_404(self, client):
        response = await client.get("/api/albums/9999")
        assert response.status_code == 404

    @pytest.mark.anyio
    async def test_update_album(self, client):
        created = await client.post("/api/albums", json={"name": "Old", "type": "manual"})
        album_id = created.json()["id"]
        response = await client.put(f"/api/albums/{album_id}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    @pytest.mark.anyio
    async def test_delete_album(self, client):
        created = await client.post("/api/albums", json={"name": "Delete", "type": "manual"})
        album_id = created.json()["id"]
        response = await client.delete(f"/api/albums/{album_id}")
        assert response.status_code == 204

    @pytest.mark.anyio
    async def test_add_images_to_manual_album_via_api(self, client):
        created = await client.post("/api/albums", json={"name": "Manual", "type": "manual"})
        album_id = created.json()["id"]
        response = await client.post(
            f"/api/albums/{album_id}/images",
            json={"content_hashes": ["hash1", "hash2"]},
        )
        assert response.status_code == 200
        assert response.json()["added"] == 2

    @pytest.mark.anyio
    async def test_cannot_add_images_to_smart_album_via_api(self, client):
        created = await client.post("/api/albums", json={"name": "Smart", "type": "smart", "rule_logic": "or"})
        album_id = created.json()["id"]
        response = await client.post(
            f"/api/albums/{album_id}/images",
            json={"content_hashes": ["hash1"]},
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_remove_images_from_manual_album_via_api(self, client):
        created = await client.post("/api/albums", json={"name": "Manual Remove", "type": "manual"})
        album_id = created.json()["id"]
        await client.post(f"/api/albums/{album_id}/images", json={"content_hashes": ["hash1"]})
        response = await client.request(
            "DELETE",
            f"/api/albums/{album_id}/images",
            json={"content_hashes": ["hash1"]},
        )
        assert response.status_code == 200
        assert response.json()["removed"] == 1

    @pytest.mark.anyio
    async def test_list_album_images_paginated(self, client):
        created = await client.post("/api/albums", json={"name": "Paginated", "type": "manual"})
        album_id = created.json()["id"]
        await client.post(
            f"/api/albums/{album_id}/images",
            json={"content_hashes": ["hash1", "hash2", "hash3"]},
        )
        response = await client.get(f"/api/albums/{album_id}/images?limit=2")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2
        assert response.json()["next_cursor"] is not None

    @pytest.mark.anyio
    async def test_set_and_get_smart_album_rules_via_api(self, client):
        created = await client.post("/api/albums", json={"name": "Rules", "type": "smart", "rule_logic": "or"})
        album_id = created.json()["id"]
        response = await client.put(
            f"/api/albums/{album_id}/rules",
            json={"rules": [{"tag_id": 1, "match_mode": "include"}]},
        )
        assert response.status_code == 200
        fetched = await client.get(f"/api/albums/{album_id}/rules")
        assert fetched.status_code == 200
        assert len(fetched.json()) == 1

    @pytest.mark.anyio
    async def test_set_rule_with_nonexistent_tag_returns_400(self, client):
        created = await client.post("/api/albums", json={"name": "Bad Rules", "type": "smart", "rule_logic": "or"})
        album_id = created.json()["id"]
        response = await client.put(
            f"/api/albums/{album_id}/rules",
            json={"rules": [{"tag_id": 9999, "match_mode": "include"}]},
        )
        assert response.status_code == 400

    @pytest.mark.anyio
    async def test_set_source_paths_via_api(self, client):
        created = await client.post("/api/albums", json={"name": "Paths", "type": "smart", "rule_logic": "or"})
        album_id = created.json()["id"]
        response = await client.put(
            f"/api/albums/{album_id}/source-paths",
            json={"paths": ["photos/travel"]},
        )
        assert response.status_code == 200
        fetched = await client.get(f"/api/albums/{album_id}/source-paths")
        assert fetched.json() == ["photos/travel"]

    @pytest.mark.anyio
    async def test_cannot_set_source_paths_for_manual_album(self, client):
        created = await client.post("/api/albums", json={"name": "Manual Paths", "type": "manual"})
        album_id = created.json()["id"]
        response = await client.put(
            f"/api/albums/{album_id}/source-paths",
            json={"paths": ["photos/travel"]},
        )
        assert response.status_code == 400
