from abc import ABC, abstractmethod
from pathlib import Path


def build_embedding_key(provider: str, model: str, version: str) -> str:
    return f"{provider}:{model}:{version}"


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
