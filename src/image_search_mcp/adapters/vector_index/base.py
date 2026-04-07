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
    def get_embedding(self, content_hash: str, embedding_key: str) -> list[float] | None: ...

    @abstractmethod
    def search(
        self,
        vector: list[float],
        limit: int,
        embedding_key: str,
        content_hash_filter: set[str] | None = None,
    ) -> list[dict]: ...

    @abstractmethod
    def count(self, embedding_key: str) -> int: ...

    @abstractmethod
    def delete_embeddings(self, content_hashes: list[str], embedding_key: str) -> int: ...
