import httpx
import pytest
import respx

from image_search_mcp.adapters.embedding.jina import JinaEmbeddingClient


@pytest.mark.anyio
@respx.mock
async def test_embed_texts_uses_configured_model() -> None:
    route = respx.post("https://api.jina.ai/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"embedding": [0.1, 0.2, 0.3]}],
                "model": "jina-clip-v2",
            },
        )
    )
    client = JinaEmbeddingClient(api_key="secret", model="jina-clip-v2")
    try:
        vectors = await client.embed_texts(["sunset"])
        assert route.called
        assert vectors == [[0.1, 0.2, 0.3]]
    finally:
        await client.aclose()


@pytest.mark.anyio
@respx.mock
async def test_embed_texts_retries_up_to_three_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("image_search_mcp.adapters.embedding.jina.asyncio.sleep", _no_sleep)

    route = respx.post("https://api.jina.ai/v1/embeddings").mock(
        side_effect=[
            httpx.Response(500, json={"error": "temporary"}),
            httpx.Response(502, json={"error": "temporary"}),
            httpx.Response(
                200,
                json={"data": [{"embedding": [0.4, 0.5]}], "model": "jina-clip-v2"},
            ),
        ]
    )

    client = JinaEmbeddingClient(api_key="secret", model="jina-clip-v2")
    try:
        vectors = await client.embed_texts(["sunset"])
        assert vectors == [[0.4, 0.5]]
        assert route.call_count == 3
    finally:
        await client.aclose()


@pytest.mark.anyio
async def test_provider_model_version_accessors() -> None:
    client = JinaEmbeddingClient(api_key="secret", model="jina-clip-v2", version="v2")
    try:
        assert client.provider() == "jina"
        assert client.model() == "jina-clip-v2"
        assert client.version() == "v2"
    finally:
        await client.aclose()
