from datetime import UTC, datetime
from pathlib import Path

import pytest
from PIL import Image

from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord
from image_search_mcp.services.search import SearchService


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.text_calls: list[list[str]] = []
        self.image_calls: list[list[Path]] = []

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.text_calls.append(texts[:])
        return [[1.0, 0.0, 0.0] for _ in texts]

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        self.image_calls.append(paths[:])
        return [[0.0, 1.0, 0.0] for _ in paths]

    def vector_dimension(self) -> int | None:
        return 3


class FakeVectorIndex:
    def __init__(
        self,
        search_results: list[dict],
        embeddings: dict[tuple[str, str], list[float]] | None = None,
    ) -> None:
        self.search_results = search_results
        self.embeddings = embeddings or {}
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

    def get_embedding(self, content_hash: str, embedding_key: str) -> list[float] | None:
        vector = self.embeddings.get((content_hash, embedding_key))
        return None if vector is None else vector[:]


class FakeRepository:
    def __init__(self, images: dict[str, ImageRecord]) -> None:
        self.images = images
        self.tag_filter_result: set[str] = set()
        self.category_filter_result: set[str] = set()
        self.tags_for_images: dict[str, list] = {}
        self.categories_for_images: dict[str, list] = {}

    def get_image(self, content_hash: str) -> ImageRecord | None:
        return self.images.get(content_hash)

    def filter_by_tags(self, tag_ids: list[int]) -> set[str]:
        return self.tag_filter_result

    def filter_by_category(self, category_id: int, include_subcategories: bool = True) -> set[str]:
        return self.category_filter_result

    def get_tags_for_images(self, content_hashes: list[str]) -> dict[str, list]:
        return {h: self.tags_for_images.get(h, []) for h in content_hashes}

    def get_categories_for_images(self, content_hashes: list[str]) -> dict[str, list]:
        return {h: self.categories_for_images.get(h, []) for h in content_hashes}


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
        ],
        embeddings={(query_hash, "jina:jina-clip-v2:v2"): [0.0, 1.0, 0.0]},
    )
    embedding_client = FakeEmbeddingClient()
    service = SearchService(
        Settings(images_root=images_root, index_root=index_root),
        repository,
        embedding_client,
        vector_index,
    )

    results = await service.search_similar(
        image_path=str(query_image),
        top_k=2,
        min_score=0.0,
        folder=None,
    )

    assert [result.content_hash for result in results] == [other_hash]
    assert embedding_client.image_calls == []


@pytest.mark.anyio
async def test_search_similar_requires_stored_embedding(tmp_path: Path):
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()

    query_image = images_root / "query.png"
    Image.new("RGB", (10, 10), color="red").save(query_image)

    embedding_client = FakeEmbeddingClient()
    service = SearchService(
        Settings(images_root=images_root, index_root=index_root),
        FakeRepository({}),
        embedding_client,
        FakeVectorIndex([]),
    )

    with pytest.raises(ValueError, match="stored embedding"):
        await service.search_similar(
            image_path=str(query_image),
            top_k=2,
            min_score=0.0,
            folder=None,
        )

    assert embedding_client.image_calls == []


@pytest.mark.anyio
async def test_search_images_uses_active_embedding_key_for_non_jina_provider(tmp_path: Path):
    images_root = tmp_path / "images"
    settings = Settings(
        images_root=images_root,
        index_root=tmp_path / "index",
        embedding_provider="gemini",
        embedding_model="gemini-embedding-2-preview",
        embedding_version="2026-03-19",
    )
    repository = FakeRepository(
        {"hash-a": build_image_record("hash-a", str(images_root / "a.jpg"))}
    )
    vector_index = FakeVectorIndex([{"content_hash": "hash-a", "score": 0.9}])
    embedding_client = FakeEmbeddingClient()
    service = SearchService(settings, repository, embedding_client, vector_index)

    results = await service.search_images(
        query="sunset beach",
        folder=None,
        top_k=5,
        min_score=0.0,
    )

    assert embedding_client.text_calls == [["sunset beach"]]
    assert results[0].content_hash == "hash-a"


@pytest.mark.anyio
async def test_search_similar_uses_active_embedding_key_for_non_jina_provider(tmp_path: Path):
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
    settings = Settings(
        images_root=images_root,
        index_root=index_root,
        embedding_provider="gemini",
        embedding_model="gemini-embedding-2-preview",
        embedding_version="2026-03-19",
    )
    repository = FakeRepository(
        {
            query_hash: build_image_record(query_hash, str(query_image)),
            other_hash: build_image_record(other_hash, str(sibling_image)),
        }
    )
    vector_index = FakeVectorIndex(
        [
            {"content_hash": query_hash, "score": 0.99},
            {"content_hash": other_hash, "score": 0.95},
        ],
        embeddings={
            (query_hash, "gemini:gemini-embedding-2-preview:2026-03-19"): [0.0, 1.0, 0.0]
        },
    )
    service = SearchService(settings, repository, FakeEmbeddingClient(), vector_index)

    results = await service.search_similar(
        image_path=str(query_image),
        top_k=2,
        min_score=0.0,
        folder=None,
    )

    assert [result.content_hash for result in results] == [other_hash]


class TestSearchWithTagFilter:
    def _make_service(
        self,
        tmp_path: Path,
        repository: FakeRepository,
        vector_index: FakeVectorIndex,
    ) -> SearchService:
        images_root = tmp_path / "images"
        settings = Settings(images_root=images_root, index_root=tmp_path / "index")
        return SearchService(settings, repository, FakeEmbeddingClient(), vector_index)

    @pytest.mark.anyio
    async def test_search_with_tag_filter_passes_hashes_to_vector_index(self, tmp_path: Path):
        """When tag_ids provided, SearchService should query repo and pass filter."""
        images_root = tmp_path / "images"
        repository = FakeRepository(
            {
                "img1": build_image_record("img1", str(images_root / "img1.jpg")),
                "img2": build_image_record("img2", str(images_root / "img2.jpg")),
            }
        )
        repository.tag_filter_result = {"img1", "img2"}
        vector_index = FakeVectorIndex(
            [
                {"content_hash": "img1", "score": 0.9},
                {"content_hash": "img2", "score": 0.8},
            ]
        )
        service = self._make_service(tmp_path, repository, vector_index)

        results = await service.search_images(
            query="test",
            folder=None,
            top_k=5,
            min_score=0.0,
            tag_ids=[1, 2],
        )

        assert vector_index.last_content_hash_filter == {"img1", "img2"}
        assert [r.content_hash for r in results] == ["img1", "img2"]

    @pytest.mark.anyio
    async def test_search_with_empty_tag_filter_returns_empty(self, tmp_path: Path):
        """When tag filter matches no images, return [] without calling vector index."""
        images_root = tmp_path / "images"
        repository = FakeRepository(
            {"img1": build_image_record("img1", str(images_root / "img1.jpg"))}
        )
        repository.tag_filter_result = set()
        vector_index = FakeVectorIndex(
            [{"content_hash": "img1", "score": 0.9}]
        )
        service = self._make_service(tmp_path, repository, vector_index)

        results = await service.search_images(
            query="test",
            folder=None,
            top_k=5,
            min_score=0.0,
            tag_ids=[1],
        )

        assert results == []
        assert vector_index.last_content_hash_filter is None

    @pytest.mark.anyio
    async def test_search_with_tag_and_category_intersects(self, tmp_path: Path):
        """When both tag_ids and category_id provided, intersection is used."""
        images_root = tmp_path / "images"
        repository = FakeRepository(
            {
                "img1": build_image_record("img1", str(images_root / "img1.jpg")),
                "img2": build_image_record("img2", str(images_root / "img2.jpg")),
                "img3": build_image_record("img3", str(images_root / "img3.jpg")),
            }
        )
        repository.tag_filter_result = {"img1", "img2"}
        repository.category_filter_result = {"img2", "img3"}
        vector_index = FakeVectorIndex(
            [{"content_hash": "img2", "score": 0.9}]
        )
        service = self._make_service(tmp_path, repository, vector_index)

        results = await service.search_images(
            query="test",
            folder=None,
            top_k=5,
            min_score=0.0,
            tag_ids=[1],
            category_id=10,
        )

        assert vector_index.last_content_hash_filter == {"img2"}
        assert [r.content_hash for r in results] == ["img2"]

    @pytest.mark.anyio
    async def test_search_results_include_tags_and_categories(self, tmp_path: Path):
        """SearchResult should have populated tags and categories."""
        from datetime import UTC, datetime

        from image_search_mcp.domain.models import Category, Tag

        images_root = tmp_path / "images"
        now = datetime.now(UTC)
        tag = Tag(id=1, name="nature", created_at=now)
        cat = Category(id=2, name="outdoors", parent_id=None, sort_order=0, created_at=now)

        repository = FakeRepository(
            {"img1": build_image_record("img1", str(images_root / "img1.jpg"))}
        )
        repository.tags_for_images = {"img1": [tag]}
        repository.categories_for_images = {"img1": [cat]}
        vector_index = FakeVectorIndex(
            [{"content_hash": "img1", "score": 0.9}]
        )
        service = self._make_service(tmp_path, repository, vector_index)

        results = await service.search_images(
            query="test",
            folder=None,
            top_k=5,
            min_score=0.0,
        )

        assert len(results) == 1
        assert results[0].tags == [tag]
        assert results[0].categories == [cat]
