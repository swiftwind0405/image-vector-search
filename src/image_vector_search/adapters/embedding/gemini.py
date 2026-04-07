import asyncio
import base64
import logging
import mimetypes
import random
import time
from pathlib import Path
from typing import Any

import httpx

from image_vector_search.adapters.embedding.base import EmbeddingClient

logger = logging.getLogger(__name__)


class GeminiEmbeddingClient(EmbeddingClient):
    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    _MAX_ATTEMPTS = 5
    _MAX_DELAY_SECONDS = 30.0

    _DEFAULT_BATCH_SIZE = 32

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        version: str | None = None,
        output_dimensionality: int | None = None,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        batch_size: int = _DEFAULT_BATCH_SIZE,
    ) -> None:
        self._api_key = api_key
        self._model = model.removeprefix("models/")
        self._version = version
        self._output_dimensionality = output_dimensionality
        self._batch_size = batch_size
        self._client = httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=60.0)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            payload = {
                "requests": [self._text_request(text, task_type="RETRIEVAL_QUERY") for text in batch]
            }
            data = await self._request_embeddings(payload, expected_count=len(batch))
            all_vectors.extend(item["values"] for item in data["embeddings"])
        return all_vectors

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        all_vectors: list[list[float]] = []
        for i in range(0, len(paths), self._batch_size):
            batch = paths[i : i + self._batch_size]
            requests = await asyncio.to_thread(self._build_image_requests, batch)
            data = await self._request_embeddings(
                {"requests": requests},
                expected_count=len(batch),
            )
            all_vectors.extend(item["values"] for item in data["embeddings"])
        return all_vectors

    def vector_dimension(self) -> int | None:
        return self._output_dimensionality

    def provider(self) -> str:
        return "gemini"

    def model(self) -> str:
        return self._model

    def version(self) -> str | None:
        return self._version

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request_embeddings(
        self,
        payload: dict[str, Any],
        *,
        expected_count: int,
    ) -> dict[str, Any]:
        delay_seconds = 1.0
        endpoint = f"/models/{self._model}:batchEmbedContents"

        for attempt in range(self._MAX_ATTEMPTS):
            t0 = time.monotonic()
            try:
                response = await self._client.post(
                    endpoint,
                    params={"key": self._api_key},
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                embeddings = data.get("embeddings")
                if not isinstance(embeddings, list):
                    raise ValueError("Gemini embeddings response missing embeddings list")
                if len(embeddings) != expected_count:
                    raise ValueError(
                        "Gemini embeddings response length mismatch: "
                        f"expected {expected_count}, got {len(embeddings)}"
                    )
                return data
            except httpx.HTTPStatusError:
                elapsed_ms = (time.monotonic() - t0) * 1000
                if (
                    response.status_code not in self._RETRYABLE_STATUS_CODES
                    or attempt == self._MAX_ATTEMPTS - 1
                ):
                    logger.error(
                        "Gemini API HTTP error: status=%d, model=%s, attempt=%d, elapsed_ms=%.0f",
                        response.status_code,
                        self._model,
                        attempt + 1,
                        elapsed_ms,
                    )
                    raise
            except httpx.RequestError as exc:
                elapsed_ms = (time.monotonic() - t0) * 1000
                if attempt == self._MAX_ATTEMPTS - 1:
                    logger.error(
                        "Gemini API request error: %s, model=%s, attempt=%d, elapsed_ms=%.0f",
                        exc,
                        self._model,
                        attempt + 1,
                        elapsed_ms,
                    )
                    raise

            await asyncio.sleep(delay_seconds * random.uniform(0.5, 1.0))
            delay_seconds = min(delay_seconds * 2, self._MAX_DELAY_SECONDS)

        raise RuntimeError("Gemini embeddings request failed after retries")

    def _text_request(self, text: str, *, task_type: str) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task_type,
        }
        if self._output_dimensionality is not None:
            request["outputDimensionality"] = self._output_dimensionality
        return request

    def _build_image_requests(self, paths: list[Path]) -> list[dict[str, Any]]:
        requests: list[dict[str, Any]] = []
        for path in paths:
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            image_data = base64.b64encode(path.read_bytes()).decode("ascii")
            request: dict[str, Any] = {
                "model": f"models/{self._model}",
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": image_data,
                            }
                        }
                    ]
                },
                "taskType": "RETRIEVAL_DOCUMENT",
            }
            if self._output_dimensionality is not None:
                request["outputDimensionality"] = self._output_dimensionality
            requests.append(request)
        return requests
