from abc import ABC, abstractmethod


class VectorIndex(ABC):
    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def ensure_collection(self, dimension: int, embedding_key: str) -> None: ...

    @abstractmethod
    def upsert_embeddings(self, records: list[dict]) -> None: ...

    @abstractmethod
    def has_embedding(self, content_hash: str, embedding_key: str) -> bool: ...

    @abstractmethod
    def search(self, vector: list[float], limit: int, embedding_key: str) -> list[dict]: ...

    @abstractmethod
    def count(self, embedding_key: str) -> int: ...
