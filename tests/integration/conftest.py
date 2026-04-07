import math
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from image_vector_search.app import create_app
from image_vector_search.config import Settings
from image_vector_search.mcp.server import build_mcp_server
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.indexing import IndexService
from image_vector_search.services.jobs import JobRunner
from image_vector_search.services.search import SearchService
from image_vector_search.services.status import StatusService


COLOR_VECTORS = {
    "red": [1.0, 0.0, 0.0],
    "orange": [0.8, 0.2, 0.0],
    "blue": [0.0, 1.0, 0.0],
    "green": [0.0, 0.0, 1.0],
}

COLOR_PIXELS = {
    "red": (255, 0, 0),
    "orange": (255, 165, 0),
    "blue": (0, 0, 255),
    "green": (0, 128, 0),
}


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.text_inputs: list[list[str]] = []
        self.image_inputs: list[list[Path]] = []

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.text_inputs.append(texts[:])
        return [self._vector_for_text(text) for text in texts]

    async def embed_images(self, paths: list[Path]) -> list[list[float]]:
        resolved_paths = [path.resolve() for path in paths]
        self.image_inputs.append(resolved_paths)
        return [self._vector_for_image(path) for path in resolved_paths]

    def vector_dimension(self) -> int | None:
        return 3

    def _vector_for_text(self, text: str) -> list[float]:
        lowered = text.lower()
        for color, vector in COLOR_VECTORS.items():
            if color in lowered:
                return vector[:]
        return [0.1, 0.1, 0.1]

    def _vector_for_image(self, path: Path) -> list[float]:
        with Image.open(path) as image:
            pixel = image.convert("RGB").getpixel((0, 0))

        best_color = min(
            COLOR_PIXELS.items(),
            key=lambda item: _distance(pixel, item[1]),
        )[0]
        return COLOR_VECTORS[best_color][:]


class InMemoryVectorIndex:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str], list[float]] = {}

    def close(self) -> None:
        return None

    def ensure_collection(self, dimension: int, embedding_key: str) -> None:
        return None

    def upsert_embeddings(self, records: list[dict]) -> None:
        for record in records:
            self.records[(record["content_hash"], record["embedding_key"])] = list(
                record["embedding"]
            )

    def has_embedding(self, content_hash: str, embedding_key: str) -> bool:
        return (content_hash, embedding_key) in self.records

    def get_embedding(self, content_hash: str, embedding_key: str) -> list[float] | None:
        vector = self.records.get((content_hash, embedding_key))
        return None if vector is None else list(vector)

    def search(
        self,
        vector: list[float],
        limit: int,
        embedding_key: str,
        content_hash_filter: set[str] | None = None,
    ) -> list[dict]:
        hits: list[dict] = []
        for (content_hash, key), stored_vector in self.records.items():
            if key != embedding_key:
                continue
            if content_hash_filter is not None and content_hash not in content_hash_filter:
                continue
            hits.append(
                {
                    "content_hash": content_hash,
                    "score": _cosine_similarity(vector, stored_vector),
                }
            )
        hits.sort(key=lambda item: item["score"], reverse=True)
        return hits[:limit]

    def count(self, embedding_key: str) -> int:
        return sum(1 for (_, key) in self.records if key == embedding_key)


@dataclass
class AppFixtureBundle:
    settings: Settings
    repository: MetadataRepository
    embedding_client: FakeEmbeddingClient
    vector_index: InMemoryVectorIndex
    index_service: IndexService
    search_service: SearchService
    status_service: StatusService
    job_runner: JobRunner
    app: object
    client: TestClient
    mcp_server: object


@pytest.fixture
def app_bundle(tmp_path: Path) -> AppFixtureBundle:
    images_root = tmp_path / "images"
    index_root = tmp_path / "index"
    images_root.mkdir()
    index_root.mkdir()

    settings = Settings(
        images_root=images_root,
        index_root=index_root,
        embedding_provider="gemini",
        embedding_model="fake-clip",
        embedding_version="2026-03",
    )
    repository = MetadataRepository(index_root / "metadata.db")
    repository.initialize_schema()
    embedding_client = FakeEmbeddingClient()
    vector_index = InMemoryVectorIndex()
    index_service = IndexService(settings, repository, embedding_client, vector_index)
    search_service = SearchService(settings, repository, embedding_client, vector_index)
    status_service = StatusService(
        settings=settings,
        repository=repository,
        vector_index=vector_index,
    )
    job_runner = JobRunner(repository, index_service)
    app = create_app(
        settings=settings,
        search_service=search_service,
        status_service=status_service,
        job_runner=job_runner,
    )
    client = TestClient(app)
    mcp_server = build_mcp_server(search_service)

    return AppFixtureBundle(
        settings=settings,
        repository=repository,
        embedding_client=embedding_client,
        vector_index=vector_index,
        index_service=index_service,
        search_service=search_service,
        status_service=status_service,
        job_runner=job_runner,
        app=app,
        client=client,
        mcp_server=mcp_server,
    )


@pytest.fixture
def image_factory(app_bundle: AppFixtureBundle):
    def create_image(
        relative_path: str,
        *,
        color: str | None = None,
        source: Path | None = None,
        size: tuple[int, int] = (12, 8),
    ) -> Path:
        image_path = app_bundle.settings.images_root / relative_path
        image_path.parent.mkdir(parents=True, exist_ok=True)
        if source is not None:
            image_path.write_bytes(source.read_bytes())
            return image_path

        Image.new("RGB", size, color=color or "red").save(image_path)
        return image_path

    return create_image


@pytest.fixture
def drain_job_queue(app_bundle: AppFixtureBundle):
    def drain() -> None:
        while True:
            job = app_bundle.job_runner.run_next()
            if job is None:
                break

    return drain


@pytest.fixture
def copy_auto_fixture_tree(app_bundle: AppFixtureBundle):
    source_root = Path(__file__).resolve().parents[1] / "fixtures" / "images" / "auto"

    def copy_tree() -> Path:
        shutil.copytree(
            source_root,
            app_bundle.settings.images_root,
            dirs_exist_ok=True,
        )
        return app_bundle.settings.images_root

    return copy_tree


def _distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(
        (left[0] - right[0]) ** 2
        + (left[1] - right[1]) ** 2
        + (left[2] - right[2]) ** 2
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
