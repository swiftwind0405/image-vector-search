import asyncio
from pathlib import Path

from PIL import Image

from image_vector_search.config import Settings
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.scanning.hashing import sha256_file
from image_vector_search.services.indexing import IndexService
from image_vector_search.services.status import StatusService


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.embed_calls: list[list[Path]] = []
        self.fail_paths: set[Path] = set()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        self.embed_calls.append([path.resolve() for path in paths])
        for path in paths:
            if path.resolve() in self.fail_paths:
                raise RuntimeError(f"failed to embed {path.name}")
        return [[1.0, 0.0, 0.0] for _ in paths]

    def vector_dimension(self) -> int | None:
        return 3

    def provider(self) -> str:
        return "fake"

    def model(self) -> str:
        return "fake-clip"

    def version(self) -> str:
        return "2026-03"


class FakeVectorIndex:
    def __init__(self) -> None:
        self.ensure_calls: list[tuple[int, str]] = []
        self.records: dict[tuple[str, str], list[float]] = {}

    def close(self) -> None:
        return None

    def ensure_collection(self, dimension: int, embedding_key: str) -> None:
        self.ensure_calls.append((dimension, embedding_key))

    def upsert_embeddings(self, records: list[dict]) -> None:
        for record in records:
            self.records[(record["content_hash"], record["embedding_key"])] = record["embedding"]

    def has_embedding(self, content_hash: str, embedding_key: str) -> bool:
        return (content_hash, embedding_key) in self.records

    def search(self, vector: list[float], limit: int, embedding_key: str) -> list[dict]:
        raise NotImplementedError

    def count(self, embedding_key: str) -> int:
        return sum(1 for _, key in self.records if key == embedding_key)


class DimensionMismatchVectorIndex(FakeVectorIndex):
    def ensure_collection(self, dimension: int, embedding_key: str) -> None:
        raise ValueError(
            "Existing Milvus collection dimension 3 does not match requested dimension 5 "
            f"for embedding space {embedding_key}. Clear the index root or choose a new "
            "collection before reindexing."
        )


def create_service(
    tmp_path: Path,
    *,
    embedding_provider: str = "gemini",
    embedding_model: str = "fake-clip",
    embedding_version: str = "2026-03",
    max_embedding_file_size_mb: int = 2,
    vector_index: FakeVectorIndex | None = None,
    repository: MetadataRepository | None = None,
) -> tuple[IndexService, MetadataRepository, FakeEmbeddingClient, FakeVectorIndex]:
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir(exist_ok=True)
    index_root.mkdir(exist_ok=True)

    settings = Settings(
        images_root=images_root,
        index_root=index_root,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        max_embedding_file_size_mb=max_embedding_file_size_mb,
    )
    repository = repository or MetadataRepository(index_root / "metadata.db")
    repository.initialize_schema()
    embedding_client = FakeEmbeddingClient()
    vector_index = vector_index or FakeVectorIndex()
    service = IndexService(settings, repository, embedding_client, vector_index)
    return service, repository, embedding_client, vector_index


def create_image(images_root: Path, relative_path: str, *, color: str | None = None, source: Path | None = None) -> Path:
    image_path = images_root / relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if source is not None:
        image_path.write_bytes(source.read_bytes())
        return image_path

    Image.new("RGB", (12, 8), color=color or "red").save(image_path)
    return image_path


def test_incremental_update_reuses_embedding_on_rename(tmp_path: Path):
    service, repository, embedding_client, _ = create_service(tmp_path)
    original = create_image(service.settings.images_root, "2024/a.jpg", color="red")

    first_report = service.run_incremental_update()
    original_hash = sha256_file(original)
    assert first_report.added == 1
    assert len(embedding_client.embed_calls) == 1

    renamed = create_image(
        service.settings.images_root,
        "2024/renamed.jpg",
        source=original,
    )
    original.unlink()

    report = service.run_incremental_update()

    image = repository.get_image(original_hash)
    assert report.added == 0
    assert report.reused == 1
    assert report.path_updated == 1
    assert len(embedding_client.embed_calls) == 1
    assert image is not None
    assert image.canonical_path == str(renamed.resolve())
    assert repository.list_active_paths(original_hash) == [str(renamed.resolve())]


def test_incremental_update_skips_unchanged_files(tmp_path: Path):
    service, _, embedding_client, _ = create_service(tmp_path)
    create_image(service.settings.images_root, "2024/a.jpg", color="blue")

    first_report = service.run_incremental_update()
    second_report = service.run_incremental_update()

    assert first_report.added == 1
    assert second_report.added == 0
    assert second_report.reused == 0
    assert second_report.skipped == 1
    assert len(embedding_client.embed_calls) == 1


def test_incremental_update_deactivates_missing_files(tmp_path: Path):
    service, repository, _, _ = create_service(tmp_path)
    image_path = create_image(service.settings.images_root, "2024/a.jpg", color="green")

    service.run_incremental_update()
    content_hash = sha256_file(image_path)

    image_path.unlink()
    report = service.run_incremental_update()

    image = repository.get_image(content_hash)
    assert report.deactivated == 1
    assert image is not None
    assert image.is_active is False
    assert repository.get_system_state("last_incremental_update_at") is not None


def test_incremental_update_rebuilds_embeddings_for_new_embedding_key(tmp_path: Path):
    service, repository, embedding_client, vector_index = create_service(
        tmp_path,
        embedding_provider="gemini",
        embedding_model="fake-clip",
        embedding_version="2026-03",
    )
    image_path = create_image(service.settings.images_root, "2024/a.jpg", color="red")

    first_report = service.run_incremental_update()
    content_hash = sha256_file(image_path)
    first_key = "gemini:fake-clip:2026-03"
    assert first_report.added == 1
    assert vector_index.has_embedding(content_hash, first_key)

    next_service, _, next_embedding_client, same_vector_index = create_service(
        tmp_path,
        embedding_provider="gemini",
        embedding_model="fake-clip",
        embedding_version="2026-04",
        vector_index=vector_index,
        repository=repository,
    )

    second_report = next_service.run_incremental_update()

    assert second_report.reused == 1
    assert len(embedding_client.embed_calls) == 1
    assert len(next_embedding_client.embed_calls) == 1
    assert same_vector_index.has_embedding(content_hash, "gemini:fake-clip:2026-04")


def test_incremental_update_records_clear_dimension_mismatch_error(tmp_path: Path):
    vector_index = DimensionMismatchVectorIndex()
    service, repository, _, _ = create_service(tmp_path, vector_index=vector_index)
    create_image(service.settings.images_root, "2024/a.jpg", color="red")

    report = service.run_incremental_update()
    status_service = StatusService(
        settings=service.settings,
        repository=repository,
        vector_index=vector_index,
    )
    status = asyncio.run(status_service.get_index_status())

    assert report.errors == 1
    assert "Clear the index root or choose a new collection" in status.last_error_summary
    assert status.embedding_provider == "gemini"
    assert status.embedding_model == "fake-clip"
    assert status.embedding_version == "2026-03"


def test_incremental_update_marks_oversized_images_as_skipped(tmp_path: Path):
    service, repository, embedding_client, vector_index = create_service(tmp_path)
    image_path = create_image(service.settings.images_root, "large.jpg", color="purple")
    image_path.write_bytes(image_path.read_bytes() + b"0" * (3 * 1024 * 1024))

    report = service.run_incremental_update()
    content_hash = sha256_file(image_path)
    image = repository.get_image(content_hash)

    assert report.skipped_oversized == 1
    assert image is not None
    assert image.embedding_status == "skipped_oversized"
    assert embedding_client.embed_calls == []
    assert vector_index.records == {}


def test_incremental_update_embeds_large_images_when_limit_disabled(tmp_path: Path):
    service, repository, embedding_client, vector_index = create_service(
        tmp_path,
        max_embedding_file_size_mb=0,
    )
    image_path = create_image(service.settings.images_root, "large.jpg", color="purple")
    image_path.write_bytes(image_path.read_bytes() + b"1" * (3 * 1024 * 1024))

    report = service.run_incremental_update()
    content_hash = sha256_file(image_path)
    image = repository.get_image(content_hash)

    assert report.added == 1
    assert image is not None
    assert image.embedding_status == "embedded"
    assert len(embedding_client.embed_calls) == 1
    assert vector_index.count("gemini:fake-clip:2026-03") == 1


def test_force_embed_images_updates_status_to_embedded(tmp_path: Path):
    service, repository, _, vector_index = create_service(tmp_path)
    image_path = create_image(service.settings.images_root, "large.jpg", color="purple")
    image_path.write_bytes(image_path.read_bytes() + b"2" * (3 * 1024 * 1024))
    service.run_incremental_update()
    content_hash = sha256_file(image_path)

    result = service.force_embed_images([content_hash])
    image = repository.get_image(content_hash)

    assert result["succeeded"] == 1
    assert result["failed"] == 0
    assert image is not None
    assert image.embedding_status == "embedded"
    assert vector_index.count("gemini:fake-clip:2026-03") == 1


def test_force_embed_images_marks_failures(tmp_path: Path):
    service, repository, embedding_client, _ = create_service(tmp_path)
    image_path = create_image(service.settings.images_root, "large.jpg", color="purple")
    image_path.write_bytes(image_path.read_bytes() + b"3" * (3 * 1024 * 1024))
    service.run_incremental_update()
    content_hash = sha256_file(image_path)
    embedding_client.fail_paths.add(image_path.resolve())

    result = service.force_embed_images([content_hash])
    image = repository.get_image(content_hash)

    assert result["succeeded"] == 0
    assert result["failed"] == 1
    assert result["errors"][0]["hash"] == content_hash
    assert image is not None
    assert image.embedding_status == "failed"
