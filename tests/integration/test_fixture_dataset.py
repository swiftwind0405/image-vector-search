from pathlib import Path

import pytest

from image_search_mcp.adapters.embedding.base import build_embedding_key
from image_search_mcp.scanning.hashing import sha256_file


@pytest.mark.asyncio
async def test_indexing_committed_fixture_dataset(app_bundle, copy_auto_fixture_tree):
    images_root = copy_auto_fixture_tree()

    job = app_bundle.job_runner.enqueue("incremental")
    completed = app_bundle.job_runner.run_next()

    assert job.status == "queued"
    assert completed is not None
    assert completed.status == "succeeded"

    active_images = app_bundle.repository.list_active_images()
    indexed_paths = {Path(image.canonical_path).relative_to(images_root).as_posix() for image in active_images}
    embedding_key = build_embedding_key(
        app_bundle.settings.embedding_provider,
        app_bundle.settings.embedding_model,
        app_bundle.settings.embedding_version,
    )

    assert len(active_images) == 8
    assert app_bundle.vector_index.count(embedding_key) == 8
    assert "folders/2024/travel/red sunset.jpg" in indexed_paths
    assert "folders/2024/人物/blue-portrait.png" in indexed_paths

    orange_hash = sha256_file(images_root / "orange-wide.jpg")
    orange_paths = {
        Path(path).relative_to(images_root).as_posix()
        for path in app_bundle.repository.list_active_paths(orange_hash)
    }
    assert orange_paths == {
        "orange-wide.jpg",
        "dup/content-same-orange-a.jpg",
        "dup/content-same-orange-b.jpg",
        "renamed/before/orange.jpg",
        "renamed/after/orange-renamed.jpg",
    }

    results = await app_bundle.search_service.search_images(
        query="orange",
        folder=None,
        top_k=3,
        min_score=0.0,
    )

    assert results
    assert results[0].content_hash == orange_hash
    assert Path(results[0].path).relative_to(images_root).as_posix() in orange_paths
