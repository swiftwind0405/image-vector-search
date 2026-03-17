from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord
from image_search_mcp.services.search import SearchService


class FakeEmbeddingClient:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        return [[0.0, 1.0, 0.0] for _ in paths]

    def vector_dimension(self) -> int | None:
        return 3


class FakeVectorIndex:
    def __init__(self, search_results: list[dict]) -> None:
        self.search_results = search_results
        self.requested_limits: list[int] = []
        self.last_content_hash_filter: set[str] | None = None

    def search(
        self,
        vector: list[float],
        limit: int,
        embedding_key: str,
        content_hash_filter: set[str] | None = None,
    ) -> list[dict]:
        self.requested_limits.append(limit)
        self.last_content_hash_filter = content_hash_filter
        results = self.search_results
        if content_hash_filter is not None:
            results = [r for r in results if r["content_hash"] in content_hash_filter]
        return results[:limit]


class FakeRepository:
    def __init__(self, images: dict[str, ImageRecord]) -> None:
        self.images = images

    def get_image(self, content_hash: str) -> ImageRecord | None:
        return self.images.get(content_hash)


def build_image_record(content_hash: str, path: str, *, is_active: bool = True) -> ImageRecord:
    now = datetime.now(UTC)
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=path,
        file_size=100,
        mtime=1.0,
        mime_type="image/jpeg",
        width=12,
        height=8,
        is_active=is_active,
        last_seen_at=now,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_search_images_oversamples_before_folder_filter(tmp_path: Path):
    images_root = tmp_path / "images"
    settings = Settings(images_root=images_root, index_root=tmp_path / "index")
    repository = FakeRepository(
        {
            "hash-a": build_image_record("hash-a", str(images_root / "2023" / "a.jpg")),
            "hash-b": build_image_record("hash-b", str(images_root / "2024" / "b.jpg")),
            "hash-c": build_image_record("hash-c", str(images_root / "2024" / "c.jpg")),
        }
    )
    vector_index = FakeVectorIndex(
        [
            {"content_hash": "hash-a", "score": 0.99},
            {"content_hash": "hash-b", "score": 0.95},
            {"content_hash": "hash-c", "score": 0.90},
        ]
    )
    service = SearchService(settings, repository, FakeEmbeddingClient(), vector_index)

    results = await service.search_images(
        query="sunset beach",
        folder=str(images_root / "2024"),
        top_k=2,
        min_score=0.2,
    )

    assert vector_index.requested_limits == [20]
    assert [result.content_hash for result in results] == ["hash-b", "hash-c"]


@pytest.mark.anyio
async def test_search_similar_excludes_self_match(tmp_path: Path):
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()

    query_image = images_root / "query.png"
    Image.new("RGB", (10, 10), color="red").save(query_image)
    sibling_image = images_root / "other.png"
    Image.new("RGB", (10, 10), color="blue").save(sibling_image)

    from image_search_mcp.scanning.hashing import sha256_file

    query_hash = sha256_file(query_image)
    other_hash = sha256_file(sibling_image)
    repository = FakeRepository(
        {
            query_hash: build_image_record(query_hash, str(images_root / "indexed-query.png")),
            other_hash: build_image_record(other_hash, str(sibling_image)),
        }
    )
    vector_index = FakeVectorIndex(
        [
            {"content_hash": query_hash, "score": 0.99},
            {"content_hash": other_hash, "score": 0.95},
        ]
    )
    service = SearchService(
        Settings(images_root=images_root, index_root=index_root),
        repository,
        FakeEmbeddingClient(),
        vector_index,
    )

    results = await service.search_similar(
        image_path=str(query_image),
        top_k=2,
        min_score=0.0,
        folder=None,
    )

    assert [result.content_hash for result in results] == [other_hash]
