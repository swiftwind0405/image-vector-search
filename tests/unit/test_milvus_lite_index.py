from pathlib import Path

import pytest
from milvus_lite.server_manager import server_manager_instance

import image_vector_search.adapters.vector_index.milvus_lite as milvus_lite_module
from image_vector_search.adapters.vector_index.base import VectorIndex
from image_vector_search.adapters.vector_index.milvus_lite import MilvusLiteIndex


def test_vector_index_contract_includes_required_methods():
    assert VectorIndex.__abstractmethods__ >= {
        "close",
        "count",
        "ensure_collection",
        "has_embedding",
        "search",
        "upsert_embeddings",
    }


def test_milvus_lite_index_creates_collection(tmp_path: Path):
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    try:
        index.ensure_collection(dimension=3, embedding_key="jina:jina-clip-v2:2026-03")
        assert index.count("jina:jina-clip-v2:2026-03") == 0
    finally:
        index.close()


def test_milvus_lite_index_rejects_existing_collection_with_different_dimension(
    tmp_path: Path,
):
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    try:
        index.ensure_collection(dimension=3, embedding_key="jina:jina-clip-v2:2026-03")

        with pytest.raises(ValueError, match="dimension"):
            index.ensure_collection(dimension=4, embedding_key="jina:jina-clip-v2:2026-03")
    finally:
        index.close()


def test_milvus_lite_index_upserts_and_searches_embeddings(tmp_path: Path):
    embedding_key = "jina:jina-clip-v2:2026-03"
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    try:
        index.ensure_collection(dimension=3, embedding_key=embedding_key)

        index.upsert_embeddings(
            [
                {
                    "content_hash": "hash-a",
                    "embedding_key": embedding_key,
                    "embedding": [1.0, 0.0, 0.0],
                },
                {
                    "content_hash": "hash-b",
                    "embedding_key": embedding_key,
                    "embedding": [0.0, 1.0, 0.0],
                },
            ]
        )

        assert index.count(embedding_key) == 2
        assert index.has_embedding("hash-a", embedding_key) is True
        assert index.has_embedding("missing", embedding_key) is False

        results = index.search([1.0, 0.0, 0.0], limit=2, embedding_key=embedding_key)
        assert [result["content_hash"] for result in results] == ["hash-a", "hash-b"]
        assert results[0]["embedding_provider"] == "jina"
        assert results[0]["embedding_model"] == "jina-clip-v2"
        assert results[0]["embedding_version"] == "2026-03"
    finally:
        index.close()


def test_milvus_lite_index_upsert_replaces_existing_content_hash(tmp_path: Path):
    embedding_key = "jina:jina-clip-v2:2026-03"
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    try:
        index.ensure_collection(dimension=3, embedding_key=embedding_key)

        index.upsert_embeddings(
            [
                {
                    "content_hash": "hash-a",
                    "embedding_key": embedding_key,
                    "embedding": [1.0, 0.0, 0.0],
                }
            ]
        )
        index.upsert_embeddings(
            [
                {
                    "content_hash": "hash-a",
                    "embedding_key": embedding_key,
                    "embedding": [0.0, 0.0, 1.0],
                }
            ]
        )

        assert index.count(embedding_key) == 1
        results = index.search([0.0, 0.0, 1.0], limit=1, embedding_key=embedding_key)
        assert [result["content_hash"] for result in results] == ["hash-a"]
    finally:
        index.close()


def test_milvus_lite_index_close_releases_local_server(tmp_path: Path):
    db_path = tmp_path / "milvus.db"
    index = MilvusLiteIndex(
        db_path=db_path,
        collection_name="image_embeddings",
    )
    index.ensure_collection(dimension=3, embedding_key="jina:jina-clip-v2:2026-03")

    assert str(db_path.resolve()) in server_manager_instance._servers

    index.close()

    assert str(db_path.resolve()) not in server_manager_instance._servers


def test_milvus_lite_index_search_with_content_hash_filter(tmp_path: Path):
    embedding_key = "jina:jina-clip-v2:2026-03"
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    try:
        index.ensure_collection(dimension=3, embedding_key=embedding_key)

        index.upsert_embeddings(
            [
                {
                    "content_hash": "hash-a",
                    "embedding_key": embedding_key,
                    "embedding": [1.0, 0.0, 0.0],
                },
                {
                    "content_hash": "hash-b",
                    "embedding_key": embedding_key,
                    "embedding": [0.9, 0.1, 0.0],
                },
                {
                    "content_hash": "hash-c",
                    "embedding_key": embedding_key,
                    "embedding": [0.8, 0.2, 0.0],
                },
            ]
        )

        results = index.search(
            [1.0, 0.0, 0.0],
            limit=10,
            embedding_key=embedding_key,
            content_hash_filter={"hash-a"},
        )
        assert [r["content_hash"] for r in results] == ["hash-a"]

        results_two = index.search(
            [1.0, 0.0, 0.0],
            limit=10,
            embedding_key=embedding_key,
            content_hash_filter={"hash-b", "hash-c"},
        )
        returned_hashes = {r["content_hash"] for r in results_two}
        assert returned_hashes == {"hash-b", "hash-c"}
    finally:
        index.close()


def test_milvus_lite_index_releases_server_if_client_construction_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    db_path = tmp_path / "milvus.db"
    released_paths: list[str] = []

    class FailingMilvusClient:
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("client init failed")

    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "start_and_get_uri",
        lambda path, address=None: f"tcp://{address}" if address else "unix:/tmp/fake-milvus.sock",
    )
    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "release_server",
        lambda path: released_paths.append(str(Path(path).resolve())),
    )
    monkeypatch.setattr(milvus_lite_module, "MilvusClient", FailingMilvusClient)

    with pytest.raises(RuntimeError, match="client init failed"):
        MilvusLiteIndex(db_path=db_path, collection_name="image_embeddings")

    assert released_paths == [str(db_path.resolve())]


def test_milvus_lite_index_constructs_client_with_uri_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    db_path = tmp_path / "milvus.db"
    calls: list[dict] = []

    class RecordingMilvusClient:
        def __init__(self, *args, **kwargs) -> None:
            calls.append({"args": args, "kwargs": kwargs})

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "start_and_get_uri",
        lambda path, address=None: f"tcp://{address}" if address else "unix:/tmp/fake-milvus.sock",
    )
    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "release_server",
        lambda path: None,
    )
    monkeypatch.setattr(milvus_lite_module, "MilvusClient", RecordingMilvusClient)

    index = MilvusLiteIndex(db_path=db_path, collection_name="image_embeddings")
    index.close()

    assert len(calls) == 1
    assert calls[0]["args"] == ()
    assert calls[0]["kwargs"]["uri"].startswith("tcp://127.0.0.1:")


def test_milvus_lite_index_starts_milvus_with_loopback_tcp_address(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    db_path = tmp_path / "milvus.db"
    server_calls: list[dict[str, str]] = []
    client_calls: list[dict] = []

    class RecordingMilvusClient:
        def __init__(self, *args, **kwargs) -> None:
            client_calls.append({"args": args, "kwargs": kwargs})

        def close(self) -> None:
            return None

    def fake_start_and_get_uri(path: str, address: str | None = None) -> str:
        server_calls.append({"path": path, "address": address or ""})
        assert address is not None
        assert address.startswith("127.0.0.1:")
        return f"tcp://{address}"

    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "start_and_get_uri",
        fake_start_and_get_uri,
    )
    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "release_server",
        lambda path: None,
    )
    monkeypatch.setattr(milvus_lite_module, "MilvusClient", RecordingMilvusClient)

    index = MilvusLiteIndex(db_path=db_path, collection_name="image_embeddings")
    index.close()

    assert server_calls == [{"path": str(db_path.resolve()), "address": client_calls[0]["kwargs"]["uri"][6:]}]


def test_milvus_lite_index_configures_safer_grpc_keepalive_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    db_path = tmp_path / "milvus.db"
    calls: list[dict] = []

    class RecordingMilvusClient:
        def __init__(self, *args, **kwargs) -> None:
            calls.append({"args": args, "kwargs": kwargs})

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "start_and_get_uri",
        lambda path, address=None: f"tcp://{address}" if address else "unix:/tmp/fake-milvus.sock",
    )
    monkeypatch.setattr(
        milvus_lite_module.server_manager_instance,
        "release_server",
        lambda path: None,
    )
    monkeypatch.setattr(milvus_lite_module, "MilvusClient", RecordingMilvusClient)

    index = MilvusLiteIndex(db_path=db_path, collection_name="image_embeddings")
    index.close()

    assert calls[0]["kwargs"]["grpc_options"] == {
        "grpc.keepalive_time_ms": 60000,
        "grpc.keepalive_timeout_ms": 10000,
        "grpc.keepalive_permit_without_calls": False,
    }
    assert calls[0]["kwargs"]["dedicated"] is True
