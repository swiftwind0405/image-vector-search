from pathlib import Path

import pytest
from fastapi.routing import Mount
from fastmcp import Client

from image_vector_search.app import create_app
from image_vector_search.config import Settings
from image_vector_search.domain.models import SearchResult
from image_vector_search.mcp.server import build_mcp_server


class FakeSearchService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def search_images(self, **kwargs) -> list[SearchResult]:
        self.calls.append(("search_images", kwargs))
        return [
            SearchResult(
                content_hash="hash-red",
                path="/data/images/red.jpg",
                score=0.91,
                width=12,
                height=8,
                mime_type="image/jpeg",
            )
        ]

    async def search_similar(self, **kwargs) -> list[SearchResult]:
        self.calls.append(("search_similar", kwargs))
        return [
            SearchResult(
                content_hash="hash-blue",
                path="/data/images/blue.jpg",
                score=0.88,
                width=12,
                height=8,
                mime_type="image/jpeg",
            )
        ]


@pytest.mark.anyio
async def test_search_images_tool_returns_structured_results():
    search_service = FakeSearchService()
    mcp_server = build_mcp_server(search_service)

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "search_images",
            {"query": "red flower", "top_k": 1},
        )

    assert result.data["results"][0]["content_hash"] == "hash-red"
    assert search_service.calls == [
        (
            "search_images",
            {"query": "red flower", "top_k": 1, "min_score": 0.0, "folder": None},
        )
    ]


@pytest.mark.anyio
async def test_search_similar_tool_returns_structured_results(tmp_path: Path):
    search_service = FakeSearchService()
    mcp_server = build_mcp_server(search_service)
    query_image = tmp_path / "query.jpg"
    query_image.write_bytes(b"jpg")

    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "search_similar",
            {"image_path": str(query_image), "top_k": 1},
        )

    assert result.data["results"][0]["content_hash"] == "hash-blue"
    assert search_service.calls == [
        (
            "search_similar",
            {
                "image_path": str(query_image),
                "top_k": 1,
                "min_score": 0.0,
                "folder": None,
            },
        )
    ]


def test_create_app_mounts_mcp_under_expected_path(tmp_path: Path):
    app = create_app(
        settings=Settings(images_root=tmp_path / "images", index_root=tmp_path / "index"),
        search_service=FakeSearchService(),
    )

    assert any(
        isinstance(route, Mount) and route.path == "/mcp"
        for route in app.router.routes
    )
