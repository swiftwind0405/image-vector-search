from abc import ABC, abstractmethod


class VectorIndex(ABC):
    @abstractmethod
    def ensure_collection(self, dimension: int, embedding_key: str) -> None: ...

    @abstractmethod
    def upsert_embeddings(self, records: list[dict]) -> None: ...

    @abstractmethod
    def search(self, vector: list[float], limit: int, embedding_key: str) -> list[dict]: ...
