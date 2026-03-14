import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from image_search_mcp.adapters.embedding.base import EmbeddingClient


class JinaEmbeddingClient(EmbeddingClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        version: str | None = None,
        base_url: str = "https://api.jina.ai/v1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._version = version
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        payload = await self._request_embeddings(texts)
        return [item["embedding"] for item in payload["data"]]

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        encoded_images = await asyncio.to_thread(self._encode_images, paths)
        payload = await self._request_embeddings(encoded_images)
        return [item["embedding"] for item in payload["data"]]

    def vector_dimension(self) -> int | None:
        return None

    def provider(self) -> str:
        return "jina"

    def model(self) -> str:
        return self._model

    def version(self) -> str | None:
        return self._version

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "JinaEmbeddingClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()

    async def _request_embeddings(
        self, inputs: list[str] | list[dict[str, str]]
    ) -> dict[str, Any]:
        payload = {"model": self._model, "input": inputs}
        delay_seconds = 0.5

        for attempt in range(3):
            try:
                response = await self._client.post(
                    "/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                embedding_items = data.get("data")
                if not isinstance(embedding_items, list):
                    raise ValueError("Jina embeddings response missing data list")
                if len(embedding_items) != len(inputs):
                    raise ValueError(
                        "Jina embeddings response data length mismatch: "
                        f"expected {len(inputs)}, got {len(embedding_items)}"
                    )
                return data
            except httpx.HTTPStatusError:
                if attempt == 2:
                    raise
                if response.status_code < 500:
                    raise
            except httpx.RequestError:
                if attempt == 2:
                    raise

            await asyncio.sleep(delay_seconds)
            delay_seconds *= 2

        raise RuntimeError("Jina embeddings request failed after retries")

    def _encode_images(self, paths: list[Path]) -> list[dict[str, str]]:
        encoded_images: list[dict[str, str]] = []
        for path in paths:
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            image_data = base64.b64encode(path.read_bytes()).decode("ascii")
            encoded_images.append({"image": f"data:{mime_type};base64,{image_data}"})
        return encoded_images
