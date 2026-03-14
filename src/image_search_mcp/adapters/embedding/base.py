from abc import ABC, abstractmethod
from pathlib import Path


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_images(self, paths: list[Path]) -> list[list[float]]: ...

    @abstractmethod
    def vector_dimension(self) -> int | None: ...
