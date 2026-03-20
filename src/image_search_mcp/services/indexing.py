import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from threading import Thread
from types import SimpleNamespace

from image_search_mcp.adapters.embedding.base import EmbeddingClient, build_embedding_key

logger = logging.getLogger(__name__)
from image_search_mcp.adapters.vector_index.base import VectorIndex
from image_search_mcp.config import Settings
from image_search_mcp.domain.models import ImagePathRecord, ImageRecord, IndexingReport
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.scanning.files import iter_image_files, to_container_path
from image_search_mcp.scanning.hashing import sha256_file
from image_search_mcp.scanning.image_metadata import read_image_metadata


class IndexService:
    def __init__(
        self,
        settings: Settings,
        repository: MetadataRepository,
        embedding_client: EmbeddingClient,
        vector_index: VectorIndex,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_client = embedding_client
        self.vector_index = vector_index
        self._embed_loop: asyncio.AbstractEventLoop | None = None
        self._embed_thread: Thread | None = None

    def run_incremental_update(self) -> IndexingReport:
        return self._run_update(state_key="last_incremental_update_at", force_rehash=False)

    def run_full_rebuild(self) -> IndexingReport:
        return self._run_update(state_key="last_full_rebuild_at", force_rehash=True)

    def _run_update(self, *, state_key: str, force_rehash: bool) -> IndexingReport:
        now = datetime.now(UTC)
        report = IndexingReport()
        seen_paths: list[str] = []
        embedding_key = self._embedding_key()

        for image_path in iter_image_files(self.settings.images_root):
            report.scanned += 1
            container_path = to_container_path(image_path, self.settings.images_root)
            seen_paths.append(container_path)
            try:
                self._process_path(
                    image_path=image_path,
                    container_path=container_path,
                    now=now,
                    embedding_key=embedding_key,
                    report=report,
                    force_rehash=force_rehash,
                )
            except Exception as exc:
                logger.error("Indexing error for %s: %s", container_path, exc)
                self.repository.set_system_state("last_error_summary", str(exc))
                report.errors += 1

        report.deactivated = self.repository.mark_unseen_paths_inactive(seen_paths, now)
        self.repository.set_system_state(state_key, now.isoformat())
        return report

    def _process_path(
        self,
        *,
        image_path: Path,
        container_path: str,
        now: datetime,
        embedding_key: str,
        report: IndexingReport,
        force_rehash: bool,
    ) -> None:
        stat = image_path.stat()
        current_file = SimpleNamespace(file_size=stat.st_size, mtime=stat.st_mtime)
        existing_path = self.repository.get_image_path(container_path)

        if (
            not force_rehash
            and existing_path is not None
            and existing_path.is_active
            and existing_path.file_size == current_file.file_size
            and existing_path.mtime == current_file.mtime
            and self.vector_index.has_embedding(existing_path.content_hash, embedding_key)
        ):
            self.repository.upsert_image_path(
                ImagePathRecord(
                    content_hash=existing_path.content_hash,
                    path=container_path,
                    file_size=existing_path.file_size,
                    mtime=existing_path.mtime,
                    is_active=True,
                    last_seen_at=now,
                    created_at=existing_path.created_at,
                    updated_at=now,
                )
            )
            report.skipped += 1
            return

        content_hash = sha256_file(image_path)
        existing_image = self.repository.get_image(content_hash)
        if existing_image is None:
            self._create_new_image(
                image_path=image_path,
                container_path=container_path,
                content_hash=content_hash,
                file_size=current_file.file_size,
                mtime=current_file.mtime,
                now=now,
                embedding_key=embedding_key,
            )
            report.added += 1
            return

        self._refresh_existing_image(
            image_path=image_path,
            container_path=container_path,
            existing_image=existing_image,
            existing_path=existing_path,
            file_size=current_file.file_size,
            mtime=current_file.mtime,
            now=now,
            embedding_key=embedding_key,
        )
        report.reused += 1
        if existing_path is None or existing_path.content_hash != content_hash:
            report.path_updated += 1

    def _create_new_image(
        self,
        *,
        image_path: Path,
        container_path: str,
        content_hash: str,
        file_size: int,
        mtime: float,
        now: datetime,
        embedding_key: str,
    ) -> None:
        metadata = read_image_metadata(image_path)
        logger.info("Embedding new image: %s (hash=%s)", container_path, content_hash[:12])
        vector = self._embed_image(image_path)
        self.vector_index.ensure_collection(dimension=len(vector), embedding_key=embedding_key)
        self.vector_index.upsert_embeddings(
            [
                {
                    "content_hash": content_hash,
                    "embedding_key": embedding_key,
                    "embedding": vector,
                }
            ]
        )

        image_record = ImageRecord(
            content_hash=content_hash,
            canonical_path=container_path,
            file_size=file_size,
            mtime=mtime,
            mime_type=metadata.mime_type,
            width=metadata.width,
            height=metadata.height,
            is_active=True,
            last_seen_at=now,
            embedding_provider=self.settings.embedding_provider,
            embedding_model=self.settings.embedding_model,
            embedding_version=self.settings.embedding_version,
            created_at=now,
            updated_at=now,
        )
        self.repository.upsert_image(image_record)
        self.repository.upsert_image_path(
            ImagePathRecord(
                content_hash=content_hash,
                path=container_path,
                file_size=file_size,
                mtime=mtime,
                is_active=True,
                last_seen_at=now,
                created_at=now,
                updated_at=now,
            )
        )

    def _refresh_existing_image(
        self,
        *,
        image_path: Path,
        container_path: str,
        existing_image: ImageRecord,
        existing_path: ImagePathRecord | None,
        file_size: int,
        mtime: float,
        now: datetime,
        embedding_key: str,
    ) -> None:
        if not self.vector_index.has_embedding(existing_image.content_hash, embedding_key):
            logger.info(
                "Re-embedding image (missing vector): %s (hash=%s, key=%s)",
                container_path,
                existing_image.content_hash[:12],
                embedding_key,
            )
            vector = self._embed_image(image_path)
            self.vector_index.ensure_collection(dimension=len(vector), embedding_key=embedding_key)
            self.vector_index.upsert_embeddings(
                [
                    {
                        "content_hash": existing_image.content_hash,
                        "embedding_key": embedding_key,
                        "embedding": vector,
                    }
                ]
            )

        self.repository.upsert_image(
            existing_image.model_copy(
                update={
                    "file_size": file_size,
                    "mtime": mtime,
                    "is_active": True,
                    "last_seen_at": now,
                    "updated_at": now,
                }
            )
        )
        self.repository.upsert_image_path(
            ImagePathRecord(
                content_hash=existing_image.content_hash,
                path=container_path,
                file_size=file_size,
                mtime=mtime,
                is_active=True,
                last_seen_at=now,
                created_at=existing_path.created_at if existing_path is not None else now,
                updated_at=now,
            )
        )

    def _embed_image(self, image_path: Path) -> list[float]:
        return self._run_embedding_task(self.embedding_client.embed_images([image_path]))[0]

    def _embedding_key(self) -> str:
        return build_embedding_key(
            self.settings.embedding_provider,
            self.settings.embedding_model,
            self.settings.embedding_version,
        )

    def _ensure_embed_loop(self) -> asyncio.AbstractEventLoop:
        """Return a persistent event loop for embedding calls.

        Using a single long-lived loop avoids the 'Event loop is closed' error
        that occurs when httpx.AsyncClient is reused across multiple
        asyncio.run() calls (each of which creates and destroys a loop).
        """
        if self._embed_loop is None or self._embed_loop.is_closed():
            self._embed_loop = asyncio.new_event_loop()
            self._embed_thread = Thread(
                target=self._embed_loop.run_forever,
                daemon=True,
                name="embed-loop",
            )
            self._embed_thread.start()
        return self._embed_loop

    def _run_embedding_task(self, coroutine):
        loop = self._ensure_embed_loop()
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        return future.result()
