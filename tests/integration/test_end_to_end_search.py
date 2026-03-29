import pytest
from fastapi.testclient import TestClient
from fastmcp import Client
from PIL import Image


def test_end_to_end_incremental_then_debug_search(app_bundle, image_factory, drain_job_queue):
    image = image_factory("2024/sunset.jpg", color="orange")

    create = app_bundle.client.post("/api/jobs/incremental")
    assert create.status_code == 202

    drain_job_queue()

    response = app_bundle.client.post(
        "/api/debug/search/text",
        json={"query": "orange sunset", "top_k": 1},
    )
    body = response.json()
    assert body["results"][0]["path"] == str(image.resolve())


def test_end_to_end_duplicate_files_collapse_to_single_result(
    app_bundle, image_factory, drain_job_queue
):
    original = image_factory("2024/original.jpg", color="red")
    duplicate = image_factory("2024/duplicate.jpg", source=original)

    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    status = app_bundle.client.get("/api/status").json()
    response = app_bundle.client.post(
        "/api/debug/search/text",
        json={"query": "red flower", "top_k": 5},
    )

    assert status["total_images"] == 1
    assert len(response.json()["results"]) == 1
    assert response.json()["results"][0]["path"] == min(
        str(original.resolve()),
        str(duplicate.resolve()),
    )


def test_end_to_end_deleted_file_becomes_inactive(app_bundle, image_factory, drain_job_queue):
    image = image_factory("2024/blue.jpg", color="blue")

    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    image.unlink()
    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    response = app_bundle.client.post(
        "/api/debug/search/text",
        json={"query": "blue ocean", "top_k": 1},
    )
    status = app_bundle.client.get("/api/status").json()

    assert response.json()["results"] == []
    assert status["active_images"] == 0


@pytest.mark.anyio
async def test_end_to_end_mcp_and_debug_search_return_renamed_canonical_path(
    app_bundle, image_factory, drain_job_queue
):
    original = image_factory("2024/orange.jpg", color="orange")
    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    renamed = image_factory("2024/orange-renamed.jpg", source=original)
    original.unlink()
    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    debug_response = app_bundle.client.post(
        "/api/debug/search/text",
        json={"query": "orange sunset", "top_k": 1},
    )

    async with Client(app_bundle.mcp_server) as client:
        mcp_response = await client.call_tool(
            "search_images",
            {"query": "orange sunset", "top_k": 1},
        )

    assert debug_response.json()["results"][0]["path"] == str(renamed.resolve())
    assert mcp_response.data["results"][0]["path"] == str(renamed.resolve())
    assert len(app_bundle.embedding_client.image_inputs) == 1


def test_end_to_end_similar_search_reuses_stored_embedding(
    app_bundle, image_factory, drain_job_queue
):
    query = image_factory("2024/orange.jpg", color="orange")
    image_factory("2024/orange-2.jpg", color="orange", size=(13, 8))

    app_bundle.client.post("/api/jobs/incremental")
    drain_job_queue()

    indexed_image_embed_calls = len(app_bundle.embedding_client.image_inputs)

    response = app_bundle.client.post(
        "/api/debug/search/similar",
        json={"image_path": str(query.resolve()), "top_k": 1},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["path"] != str(query.resolve())
    assert len(app_bundle.embedding_client.image_inputs) == indexed_image_embed_calls


def test_end_to_end_reindexes_for_active_embedding_key_change(
    tmp_path
):
    import math
    from pathlib import Path

    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()

    from fastapi.testclient import TestClient

    from image_search_mcp.app import create_app
    from image_search_mcp.config import Settings
    from image_search_mcp.repositories.sqlite import MetadataRepository
    from image_search_mcp.services.indexing import IndexService
    from image_search_mcp.services.jobs import JobRunner
    from image_search_mcp.services.search import SearchService
    from image_search_mcp.services.status import StatusService

    class FakeEmbeddingClient:
        def __init__(self) -> None:
            self.text_inputs: list[list[str]] = []
            self.image_inputs: list[list[Path]] = []

        async def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.text_inputs.append(texts[:])
            return [[0.8, 0.2, 0.0] for _ in texts]

        async def embed_images(self, paths: list[Path]) -> list[list[float]]:
            resolved_paths = [path.resolve() for path in paths]
            self.image_inputs.append(resolved_paths)
            return [[0.8, 0.2, 0.0] for _ in resolved_paths]

        def vector_dimension(self) -> int | None:
            return 3

    class InMemoryVectorIndex:
        def __init__(self) -> None:
            self.records: dict[tuple[str, str], list[float]] = {}

        def close(self) -> None:
            return None

        def ensure_collection(self, dimension: int, embedding_key: str) -> None:
            return None

        def upsert_embeddings(self, records: list[dict]) -> None:
            for record in records:
                self.records[(record["content_hash"], record["embedding_key"])] = list(
                    record["embedding"]
                )

        def has_embedding(self, content_hash: str, embedding_key: str) -> bool:
            return (content_hash, embedding_key) in self.records

        def get_embedding(self, content_hash: str, embedding_key: str) -> list[float] | None:
            vector = self.records.get((content_hash, embedding_key))
            return None if vector is None else list(vector)

        def search(
            self,
            vector: list[float],
            limit: int,
            embedding_key: str,
            content_hash_filter: set[str] | None = None,
        ) -> list[dict]:
            hits: list[dict] = []
            for (content_hash, key), stored_vector in self.records.items():
                if key != embedding_key:
                    continue
                if content_hash_filter is not None and content_hash not in content_hash_filter:
                    continue
                numerator = sum(a * b for a, b in zip(vector, stored_vector, strict=True))
                left_norm = math.sqrt(sum(value * value for value in vector))
                right_norm = math.sqrt(sum(value * value for value in stored_vector))
                score = 0.0 if left_norm == 0 or right_norm == 0 else numerator / (left_norm * right_norm)
                hits.append({"content_hash": content_hash, "score": score})
            hits.sort(key=lambda item: item["score"], reverse=True)
            return hits[:limit]

        def count(self, embedding_key: str) -> int:
            return sum(1 for (_, key) in self.records if key == embedding_key)

    settings_v1 = Settings(
        images_root=images_root,
        index_root=index_root,
        embedding_provider="gemini",
        embedding_model="fake-clip",
        embedding_version="2026-03",
    )
    repository = MetadataRepository(index_root / "metadata.db")
    repository.initialize_schema()
    vector_index = InMemoryVectorIndex()
    embedding_client_v1 = FakeEmbeddingClient()
    index_service_v1 = IndexService(settings_v1, repository, embedding_client_v1, vector_index)
    job_runner_v1 = JobRunner(repository, index_service_v1)
    search_service_v1 = SearchService(settings_v1, repository, embedding_client_v1, vector_index)
    status_service_v1 = StatusService(settings=settings_v1, repository=repository, vector_index=vector_index)
    client_v1 = TestClient(
        create_app(
            settings=settings_v1,
            search_service=search_service_v1,
            status_service=status_service_v1,
            job_runner=job_runner_v1,
        )
    )

    image_path = images_root / "2024" / "sunset.jpg"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    from PIL import Image

    Image.new("RGB", (12, 8), color="orange").save(image_path)
    client_v1.post("/api/jobs/incremental")
    while job_runner_v1.run_next() is not None:
        pass

    settings_v2 = Settings(
        images_root=images_root,
        index_root=index_root,
        embedding_provider="gemini",
        embedding_model="fake-clip",
        embedding_version="2026-04",
    )
    embedding_client_v2 = FakeEmbeddingClient()
    index_service_v2 = IndexService(settings_v2, repository, embedding_client_v2, vector_index)
    job_runner_v2 = JobRunner(repository, index_service_v2)
    search_service_v2 = SearchService(settings_v2, repository, embedding_client_v2, vector_index)
    status_service_v2 = StatusService(settings=settings_v2, repository=repository, vector_index=vector_index)
    client_v2 = TestClient(
        create_app(
            settings=settings_v2,
            search_service=search_service_v2,
            status_service=status_service_v2,
            job_runner=job_runner_v2,
        )
    )

    client_v2.post("/api/jobs/incremental")
    while job_runner_v2.run_next() is not None:
        pass

    status = client_v2.get("/api/status").json()

    assert len(embedding_client_v1.image_inputs) == 1
    assert len(embedding_client_v2.image_inputs) == 1
    assert status["embedding_version"] == "2026-04"
    assert status["vector_entries"] == 1


def test_end_to_end_similar_search_requires_indexed_image(app_bundle, tmp_path):
    unindexed = app_bundle.settings.images_root / "unindexed.png"
    Image.new("RGB", (10, 10), color="red").save(unindexed)

    client = TestClient(app_bundle.app, raise_server_exceptions=False)
    response = client.post(
        "/api/debug/search/similar",
        json={"image_path": str(unindexed), "top_k": 1},
    )

    assert response.status_code == 400
    assert "stored embedding" in response.json()["detail"]
