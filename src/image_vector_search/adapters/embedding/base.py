from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


def build_embedding_key(provider: str, model: str, version: str | None) -> str:
    v = version if version is not None else "default"
    return f"{provider}:{model}:{v}"


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_images(self, paths: list[Path]) -> list[list[float]]: ...

    @abstractmethod
    def vector_dimension(self) -> int | None: ...

    @abstractmethod
    def provider(self) -> str: ...

    @abstractmethod
    def model(self) -> str: ...

    @abstractmethod
    def version(self) -> str | None: ...

    @abstractmethod
    async def aclose(self) -> None: ...

    async def __aenter__(self) -> "EmbeddingClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        await self.aclose()
