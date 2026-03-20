import json
from pathlib import Path

import httpx
import pytest
import respx

from image_search_mcp.adapters.embedding.gemini import GeminiEmbeddingClient


@pytest.mark.anyio
@respx.mock
async def test_embed_texts_uses_expected_gemini_request_shape() -> None:
    route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:batchEmbedContents"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"embeddings": [{"values": [0.1, 0.2, 0.3]}]},
        )
    )
    client = GeminiEmbeddingClient(
        api_key="secret",
        model="gemini-embedding-2-preview",
    )
    try:
        vectors = await client.embed_texts(["sunset"])
        assert vectors == [[0.1, 0.2, 0.3]]
        request_payload = json.loads(route.calls[0].request.content.decode())
        assert request_payload["requests"] == [
            {
                "model": "models/gemini-embedding-2-preview",
                "content": {
                    "parts": [{"text": "sunset"}],
                },
                "taskType": "RETRIEVAL_QUERY",
            }
        ]
    finally:
        await client.aclose()


@pytest.mark.anyio
@respx.mock
async def test_embed_images_base64_encodes_image_parts(tmp_path: Path) -> None:
    route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:batchEmbedContents"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"embeddings": [{"values": [0.7, 0.8]}]},
        )
    )
    image_path = tmp_path / "sample.png"
    image_path.write_bytes(b"png-bytes")

    client = GeminiEmbeddingClient(
        api_key="secret",
        model="gemini-embedding-2-preview",
    )
    try:
        vectors = await client.embed_images([image_path])
        assert vectors == [[0.7, 0.8]]
        request_payload = json.loads(route.calls[0].request.content.decode())
        inline_data = request_payload["requests"][0]["content"]["parts"][0]["inlineData"]
        assert inline_data == {
            "mimeType": "image/png",
            "data": "cG5nLWJ5dGVz",
        }
    finally:
        await client.aclose()


@pytest.mark.anyio
@respx.mock
async def test_embed_texts_retries_transient_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("image_search_mcp.adapters.embedding.gemini.asyncio.sleep", _no_sleep)

    route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2-preview:batchEmbedContents"
    ).mock(
        side_effect=[
            httpx.Response(503, json={"error": "temporary"}),
            httpx.Response(200, json={"embeddings": [{"values": [0.4, 0.5]}]}),
        ]
    )
    client = GeminiEmbeddingClient(
        api_key="secret",
        model="gemini-embedding-2-preview",
    )
    try:
        vectors = await client.embed_texts(["sunset"])
        assert vectors == [[0.4, 0.5]]
        assert route.call_count == 2
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_vector_dimension_reports_configured_output_dimensionality() -> None:
    client = GeminiEmbeddingClient(
        api_key="secret",
        model="gemini-embedding-2-preview",
        output_dimensionality=512,
    )
    try:
        assert client.vector_dimension() == 512
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_vector_dimension_is_none_without_configured_dimensionality() -> None:
    client = GeminiEmbeddingClient(
        api_key="secret",
        model="gemini-embedding-2-preview",
    )
    try:
        assert client.vector_dimension() is None
    finally:
        await client.aclose()
