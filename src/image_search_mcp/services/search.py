from pathlib import Path

from image_search_mcp.adapters.embedding.base import EmbeddingClient
from image_search_mcp.adapters.vector_index.base import VectorIndex
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord, SearchResult
from image_search_mcp.scanning.files import to_container_path
from image_search_mcp.scanning.hashing import sha256_file


class SearchService:
    def __init__(
        self,
        settings: Settings,
        repository,
        embedding_client: EmbeddingClient,
        vector_index: VectorIndex,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_client = embedding_client
        self.vector_index = vector_index

    async def search_images(
        self,
        *,
        query: str,
        folder: str | None,
        top_k: int,
        min_score: float,
    ) -> list[SearchResult]:
        vector = (await self.embedding_client.embed_texts([query]))[0]
        raw_results = self.vector_index.search(
            vector,
            limit=self._candidate_limit(top_k),
            embedding_key=self._embedding_key(),
        )
        return self._resolve_results(
            raw_results=raw_results,
            folder=folder,
            top_k=top_k,
            min_score=min_score,
        )

    async def search_similar(
        self,
        *,
        image_path: str,
        top_k: int,
        min_score: float,
        folder: str | None,
    ) -> list[SearchResult]:
        query_path = Path(image_path).resolve()
        if not query_path.exists():
            raise FileNotFoundError(query_path)
        to_container_path(query_path, self.settings.images_root)

        vector = (await self.embedding_client.embed_images([query_path]))[0]
        raw_results = self.vector_index.search(
            vector,
            limit=self._candidate_limit(top_k),
            embedding_key=self._embedding_key(),
        )
        return self._resolve_results(
            raw_results=raw_results,
            folder=folder,
            top_k=top_k,
            min_score=min_score,
            exclude_content_hash=sha256_file(query_path),
        )

    def _resolve_results(
        self,
        *,
        raw_results: list[dict],
        folder: str | None,
        top_k: int,
        min_score: float,
        exclude_content_hash: str | None = None,
    ) -> list[SearchResult]:
        folder_path = Path(folder).resolve() if folder else None
        results: list[SearchResult] = []

        for raw_result in raw_results:
            content_hash = str(raw_result["content_hash"])
            if exclude_content_hash is not None and content_hash == exclude_content_hash:
                continue

            score = float(raw_result.get("score", raw_result.get("distance", 0.0)))
            if score < min_score:
                continue

            image = self.repository.get_image(content_hash)
            if image is None or not image.is_active:
                continue
            if folder_path is not None and not self._is_inside_folder(
                image.canonical_path, folder_path
            ):
                continue

            results.append(self._to_search_result(image, score))
            if len(results) >= top_k:
                break

        return results

    def _candidate_limit(self, top_k: int) -> int:
        return min(max(top_k * 5, 20), 200)

    def _embedding_key(self) -> str:
        return (
            f"{self.settings.embedding_provider}:"
            f"{self.settings.embedding_model}:"
            f"{self.settings.embedding_version}"
        )

    def _is_inside_folder(self, image_path: str, folder_path: Path) -> bool:
        candidate_path = Path(image_path).resolve()
        try:
            candidate_path.relative_to(folder_path)
        except ValueError:
            return False
        return True

    def _to_search_result(self, image: ImageRecord, score: float) -> SearchResult:
        return SearchResult(
            content_hash=image.content_hash,
            path=image.canonical_path,
            score=score,
            width=image.width,
            height=image.height,
            mime_type=image.mime_type,
        )
