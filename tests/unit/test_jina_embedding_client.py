import httpx
import json
import pytest
import respx
from pathlib import Path

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
        request_payload = json.loads(route.calls[0].request.content.decode())
        assert request_payload["model"] == "jina-clip-v2"
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


@pytest.mark.anyio
@respx.mock
async def test_embed_texts_raises_on_partial_embeddings_response() -> None:
    respx.post("https://api.jina.ai/v1/embeddings").mock(
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
        with pytest.raises(ValueError, match="response data length mismatch"):
            await client.embed_texts(["sunset", "ocean"])
    finally:
        await client.aclose()


@pytest.mark.anyio
@respx.mock
async def test_embed_images_uses_to_thread_and_sends_expected_payload(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    route = respx.post("https://api.jina.ai/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ],
                "model": "jina-clip-v2",
            },
        )
    )
    to_thread_calls: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

    async def _fake_to_thread(func: object, /, *args: object, **kwargs: object) -> object:
        to_thread_calls.append((func, args, kwargs))
        return func(*args, **kwargs)  # type: ignore[misc]

    monkeypatch.setattr(
        "image_search_mcp.adapters.embedding.jina.asyncio.to_thread", _fake_to_thread
    )

    image_one = tmp_path / "one.png"
    image_two = tmp_path / "two.jpg"
    image_one.write_bytes(b"png-bytes")
    image_two.write_bytes(b"jpg-bytes")

    client = JinaEmbeddingClient(api_key="secret", model="jina-clip-v2")
    try:
        vectors = await client.embed_images([image_one, image_two])
        assert vectors == [[0.1, 0.2], [0.3, 0.4]]
        assert to_thread_calls
        request_payload = json.loads(route.calls[0].request.content.decode())
        assert request_payload["model"] == "jina-clip-v2"
        assert request_payload["input"] == [
            {"image": "data:image/png;base64,cG5nLWJ5dGVz"},
            {"image": "data:image/jpeg;base64,anBnLWJ5dGVz"},
        ]
    finally:
        await client.aclose()
