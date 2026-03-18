import asyncio
import base64
import logging
import mimetypes
import time
from pathlib import Path
from typing import Any

import httpx

from image_search_mcp.adapters.embedding.base import EmbeddingClient

logger = logging.getLogger(__name__)


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
        logger.debug("Jina embed_texts: count=%d", len(texts))
        payload = await self._request_embeddings(texts)
        return [item["embedding"] for item in payload["data"]]

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        logger.debug("Jina embed_images: count=%d, paths=%s", len(paths), [p.name for p in paths])
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
        input_type = "image" if inputs and isinstance(inputs[0], dict) else "text"
        payload = {"model": self._model, "input": inputs}
        delay_seconds = 0.5

        logger.info(
            "Jina API request: model=%s, input_type=%s, count=%d",
            self._model,
            input_type,
            len(inputs),
        )

        for attempt in range(3):
            t0 = time.monotonic()
            try:
                response = await self._client.post(
                    "/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                elapsed_ms = (time.monotonic() - t0) * 1000
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
                usage = data.get("usage", {})
                logger.info(
                    "Jina API success: model=%s, input_type=%s, count=%d, elapsed_ms=%.0f, tokens=%s",
                    self._model,
                    input_type,
                    len(embedding_items),
                    elapsed_ms,
                    usage.get("total_tokens", "n/a"),
                )
                return data
            except httpx.HTTPStatusError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                if attempt == 2 or response.status_code < 500:
                    logger.error(
                        "Jina API HTTP error: status=%d, model=%s, attempt=%d, elapsed_ms=%.0f",
                        response.status_code,
                        self._model,
                        attempt + 1,
                        elapsed_ms,
                    )
                    raise
                logger.warning(
                    "Jina API HTTP error (will retry): status=%d, model=%s, attempt=%d/%d, elapsed_ms=%.0f",
                    response.status_code,
                    self._model,
                    attempt + 1,
                    3,
                    elapsed_ms,
                )
            except httpx.RequestError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                if attempt == 2:
                    logger.error(
                        "Jina API request error: %s, model=%s, attempt=%d, elapsed_ms=%.0f",
                        exc,
                        self._model,
                        attempt + 1,
                        elapsed_ms,
                    )
                    raise
                logger.warning(
                    "Jina API request error (will retry): %s, model=%s, attempt=%d/%d, elapsed_ms=%.0f",
                    exc,
                    self._model,
                    attempt + 1,
                    3,
                    elapsed_ms,
                )

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
