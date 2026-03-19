import logging
from pathlib import Path

from image_search_mcp.adapters.embedding.base import EmbeddingClient
from image_search_mcp.adapters.vector_index.base import VectorIndex
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImageRecord, SearchResult
from image_search_mcp.scanning.files import to_container_path
from image_search_mcp.scanning.hashing import sha256_file

logger = logging.getLogger(__name__)


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
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        include_subcategories: bool = True,
    ) -> list[SearchResult]:
        logger.info(
            "Text search: query=%r, top_k=%d, min_score=%.2f, folder=%s",
            query[:100],
            top_k,
            min_score,
            folder,
        )
        content_hash_filter = self._build_content_hash_filter(
            tag_ids=tag_ids,
            category_id=category_id,
            include_subcategories=include_subcategories,
        )
        if content_hash_filter is not None and not content_hash_filter:
            logger.debug("Text search: empty content_hash_filter, returning no results")
            return []

        vector = (await self.embedding_client.embed_texts([query]))[0]
        raw_results = self.vector_index.search(
            vector,
            limit=self._candidate_limit(top_k),
            embedding_key=self._embedding_key(),
            content_hash_filter=content_hash_filter,
        )
        results = self._resolve_results(
            raw_results=raw_results,
            folder=folder,
            top_k=top_k,
            min_score=min_score,
        )
        self._enrich_results(results)
        logger.info("Text search complete: %d results for query=%r", len(results), query[:100])
        return results

    async def search_similar(
        self,
        *,
        image_path: str,
        top_k: int,
        min_score: float,
        folder: str | None,
        tag_ids: list[int] | None = None,
        category_id: int | None = None,
        include_subcategories: bool = True,
    ) -> list[SearchResult]:
        logger.info(
            "Image similarity search: path=%s, top_k=%d, min_score=%.2f, folder=%s",
            image_path,
            top_k,
            min_score,
            folder,
        )
        query_path = Path(image_path).resolve()
        if not query_path.exists():
            logger.error("Image similarity search: file not found: %s", query_path)
            raise FileNotFoundError(query_path)
        to_container_path(query_path, self.settings.images_root)

        content_hash_filter = self._build_content_hash_filter(
            tag_ids=tag_ids,
            category_id=category_id,
            include_subcategories=include_subcategories,
        )
        if content_hash_filter is not None and not content_hash_filter:
            logger.debug("Image similarity search: empty content_hash_filter, returning no results")
            return []

        query_hash = sha256_file(query_path)
        vector = self.vector_index.get_embedding(query_hash, self._embedding_key())
        if vector is None:
            logger.warning(
                "Image similarity search: no stored embedding for hash=%s, path=%s",
                query_hash[:12],
                query_path,
            )
            raise ValueError(
                "Image similarity search requires a stored embedding. "
                "Index the image before searching for similar images."
            )
        raw_results = self.vector_index.search(
            vector,
            limit=self._candidate_limit(top_k),
            embedding_key=self._embedding_key(),
            content_hash_filter=content_hash_filter,
        )
        results = self._resolve_results(
            raw_results=raw_results,
            folder=folder,
            top_k=top_k,
            min_score=min_score,
            exclude_content_hash=query_hash,
        )
        self._enrich_results(results)
        logger.info("Image similarity search complete: %d results for path=%s", len(results), image_path)
        return results

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

    def _build_content_hash_filter(
        self,
        *,
        tag_ids: list[int] | None,
        category_id: int | None,
        include_subcategories: bool,
    ) -> set[str] | None:
        if not tag_ids and category_id is None:
            return None
        sets: list[set[str]] = []
        if tag_ids:
            sets.append(self.repository.filter_by_tags(tag_ids))
        if category_id is not None:
            sets.append(self.repository.filter_by_category(category_id, include_subcategories))
        content_hash_filter = sets[0]
        for s in sets[1:]:
            content_hash_filter &= s
        return content_hash_filter

    def _enrich_results(self, results: list[SearchResult]) -> None:
        if not results:
            return
        hashes = [r.content_hash for r in results]
        tags_map = self.repository.get_tags_for_images(hashes)
        cats_map = self.repository.get_categories_for_images(hashes)
        for r in results:
            r.tags = tags_map.get(r.content_hash, [])
            r.categories = cats_map.get(r.content_hash, [])

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
