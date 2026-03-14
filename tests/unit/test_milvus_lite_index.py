from pathlib import Path

from image_search_mcp.adapters.vector_index.milvus_lite import MilvusLiteIndex


def test_milvus_lite_index_creates_collection(tmp_path: Path):
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
    index.ensure_collection(dimension=3, embedding_key="jina:jina-clip-v2:2026-03")
    assert index.count("jina:jina-clip-v2:2026-03") == 0


def test_milvus_lite_index_upserts_and_searches_embeddings(tmp_path: Path):
    embedding_key = "jina:jina-clip-v2:2026-03"
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
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


def test_milvus_lite_index_upsert_replaces_existing_content_hash(tmp_path: Path):
    embedding_key = "jina:jina-clip-v2:2026-03"
    index = MilvusLiteIndex(
        db_path=tmp_path / "milvus.db",
        collection_name="image_embeddings",
    )
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
