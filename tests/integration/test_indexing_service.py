from pathlib import Path

from PIL import Image

from image_search_mcp.config import Settings
from image_search_mcp.repositories.sqlite import MetadataRepository
from image_search_mcp.scanning.hashing import sha256_file
from image_search_mcp.services.indexing import IndexService


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.embed_calls: list[list[Path]] = []

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        self.embed_calls.append([path.resolve() for path in paths])
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


def create_service(tmp_path: Path) -> tuple[IndexService, MetadataRepository, FakeEmbeddingClient]:
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()

    settings = Settings(images_root=images_root, index_root=index_root)
    repository = MetadataRepository(index_root / "metadata.db")
    repository.initialize_schema()
    embedding_client = FakeEmbeddingClient()
    vector_index = FakeVectorIndex()
    service = IndexService(settings, repository, embedding_client, vector_index)
    return service, repository, embedding_client


def create_image(images_root: Path, relative_path: str, *, color: str | None = None, source: Path | None = None) -> Path:
    image_path = images_root / relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    if source is not None:
        image_path.write_bytes(source.read_bytes())
        return image_path

    Image.new("RGB", (12, 8), color=color or "red").save(image_path)
    return image_path


def test_incremental_update_reuses_embedding_on_rename(tmp_path: Path):
    service, repository, embedding_client = create_service(tmp_path)
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
    service, _, embedding_client = create_service(tmp_path)
    create_image(service.settings.images_root, "2024/a.jpg", color="blue")

    first_report = service.run_incremental_update()
    second_report = service.run_incremental_update()

    assert first_report.added == 1
    assert second_report.added == 0
    assert second_report.reused == 0
    assert second_report.skipped == 1
    assert len(embedding_client.embed_calls) == 1


def test_incremental_update_deactivates_missing_files(tmp_path: Path):
    service, repository, _ = create_service(tmp_path)
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
