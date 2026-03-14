import pytest
from fastmcp import Client


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
