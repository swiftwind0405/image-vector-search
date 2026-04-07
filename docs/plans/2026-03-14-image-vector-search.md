# Image Vector Search Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-process Python service that exposes image search to agents via MCP and exposes indexing, rebuild, status, and debug search to humans via a lightweight web admin UI.

**Architecture:** Use one FastAPI application as the outer web container, mount a FastMCP ASGI app under `/mcp`, and keep all business logic in shared services. Persist metadata, path state, jobs, and system status in SQLite; persist embeddings in Milvus Lite; isolate the embedding provider and vector index behind narrow adapter interfaces so the embedding model can be swapped later without rewriting service code.

**Tech Stack:** Python 3.12, FastAPI, FastMCP, Pydantic Settings, httpx, SQLite, pymilvus (Milvus Lite), Pillow, Jinja2, HTMX, pytest

---

### Task 1: Bootstrap The Python Service

**Files:**
- Create: `pyproject.toml`
- Create: `src/image_vector_search/__init__.py`
- Create: `src/image_vector_search/app.py`
- Create: `src/image_vector_search/config.py`
- Create: `tests/unit/test_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from image_vector_search.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.images_root == Path("/data/images")
    assert settings.index_root == Path("/data/index")
    assert settings.default_top_k == 5
    assert settings.max_top_k == 50
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'image_vector_search'`

**Step 3: Write minimal implementation**

```toml
[project]
name = "image-search-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115,<1",
  "fastmcp>=3,<4",
  "httpx>=0.28,<1",
  "jinja2>=3.1,<4",
  "pillow>=11,<12",
  "pydantic-settings>=2.8,<3",
  "pymilvus>=2.5,<3",
  "python-multipart>=0.0.9,<1",
  "uvicorn[standard]>=0.34,<1",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.26,<1",
  "respx>=0.22,<1",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMAGE_SEARCH_", extra="ignore")

    app_name: str = "image-search-mcp"
    images_root: Path = Path("/data/images")
    index_root: Path = Path("/data/index")
    host: str = "0.0.0.0"
    port: int = 8000
    default_top_k: int = 5
    max_top_k: int = 50
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/image_vector_search/__init__.py src/image_vector_search/app.py src/image_vector_search/config.py tests/unit/test_config.py
git commit -m "feat: bootstrap python service"
```

### Task 2: Define Domain Models And SQLite Schema

**Files:**
- Create: `src/image_vector_search/domain/models.py`
- Create: `src/image_vector_search/repositories/schema.sql`
- Create: `tests/unit/test_domain_models.py`

**Step 1: Write the failing test**

```python
from image_vector_search.domain.models import SearchResult, SearchFilters


def test_search_filters_normalizes_folder():
    filters = SearchFilters(folder="/data/images/2024", top_k=3, min_score=0.2)
    assert filters.folder == "/data/images/2024"
    assert filters.top_k == 3
    assert filters.min_score == 0.2


def test_search_result_serialization():
    result = SearchResult(
        content_hash="abc",
        path="/data/images/a.jpg",
        score=0.9,
        width=100,
        height=80,
        mime_type="image/jpeg",
    )
    assert result.model_dump()["content_hash"] == "abc"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_domain_models.py -v`
Expected: FAIL because `image_vector_search.domain.models` does not exist

**Step 3: Write minimal implementation**

```python
from datetime import datetime

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    folder: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    min_score: float = Field(default=0.0, ge=-1.0, le=1.0)


class SearchResult(BaseModel):
    content_hash: str
    path: str
    score: float
    width: int
    height: int
    mime_type: str


class JobRecord(BaseModel):
    id: str
    job_type: str
    status: str
    requested_at: datetime
```

```sql
CREATE TABLE IF NOT EXISTS images (
  content_hash TEXT PRIMARY KEY,
  canonical_path TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  mtime REAL NOT NULL,
  mime_type TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  is_active INTEGER NOT NULL,
  last_seen_at TEXT NOT NULL,
  embedding_provider TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_paths (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_hash TEXT NOT NULL,
  path TEXT NOT NULL UNIQUE,
  file_size INTEGER NOT NULL,
  mtime REAL NOT NULL,
  is_active INTEGER NOT NULL,
  last_seen_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  summary_json TEXT,
  error_text TEXT
);

CREATE TABLE IF NOT EXISTS system_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_domain_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/domain/models.py src/image_vector_search/repositories/schema.sql tests/unit/test_domain_models.py
git commit -m "feat: define domain models and schema"
```

### Task 3: Implement SQLite Repository And Canonical Path Rules

**Files:**
- Create: `src/image_vector_search/repositories/sqlite.py`
- Create: `tests/unit/test_sqlite_repository.py`
- Modify: `src/image_vector_search/domain/models.py`

**Step 1: Write the failing test**

```python
from image_vector_search.repositories.sqlite import choose_canonical_path


def test_choose_canonical_path_keeps_existing_active_path():
    existing = "/data/images/2024/a.jpg"
    active_paths = ["/data/images/2024/a.jpg", "/data/images/2024/b.jpg"]
    assert choose_canonical_path(existing, active_paths) == existing


def test_choose_canonical_path_falls_back_to_sorted_active_path():
    active_paths = ["/data/images/z.jpg", "/data/images/a.jpg"]
    assert choose_canonical_path(None, active_paths) == "/data/images/a.jpg"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_sqlite_repository.py -v`
Expected: FAIL because repository helpers are missing

**Step 3: Write minimal implementation**

```python
import sqlite3
from pathlib import Path


def choose_canonical_path(existing: str | None, active_paths: list[str]) -> str | None:
    if existing and existing in active_paths:
        return existing
    if not active_paths:
        return None
    return sorted(active_paths)[0]


class MetadataRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
```

Add repository methods for:

- schema initialization
- upserting `images`
- upserting `image_paths`
- listing active paths for a `content_hash`
- marking unseen paths inactive
- reading status aggregates
- creating/updating jobs

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_sqlite_repository.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/domain/models.py src/image_vector_search/repositories/sqlite.py tests/unit/test_sqlite_repository.py
git commit -m "feat: add sqlite metadata repository"
```

### Task 4: Add Embedding Abstraction And Jina Client

**Files:**
- Create: `src/image_vector_search/adapters/embedding/base.py`
- Create: `src/image_vector_search/adapters/embedding/jina.py`
- Create: `tests/unit/test_jina_embedding_client.py`
- Modify: `src/image_vector_search/config.py`

**Step 1: Write the failing test**

```python
import pytest
import respx
import httpx

from image_vector_search.adapters.embedding.jina import JinaEmbeddingClient


@pytest.mark.asyncio
@respx.mock
async def test_embed_texts_uses_configured_model():
    route = respx.post("https://api.jina.ai/v1/embeddings").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [{"embedding": [0.1, 0.2, 0.3]}],
                "model": "jina-clip-v2",
            },
        )
    )
    client = JinaEmbeddingClient(api_key="secret", model="jina-clip-v2")
    vectors = await client.embed_texts(["sunset"])
    assert route.called
    assert vectors == [[0.1, 0.2, 0.3]]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_jina_embedding_client.py -v`
Expected: FAIL because embedding adapter files do not exist

**Step 3: Write minimal implementation**

```python
from abc import ABC, abstractmethod
from pathlib import Path


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    async def embed_images(self, paths: list[Path]) -> list[list[float]]: ...

    @abstractmethod
    def vector_dimension(self) -> int | None: ...
```

```python
import base64
from pathlib import Path

import httpx


class JinaEmbeddingClient:
    def __init__(self, api_key: str, model: str, base_url: str = "https://api.jina.ai/v1") -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.AsyncClient(base_url=base_url, timeout=60.0)
```

Implement:

- text embedding request method
- image embedding request method
- 3-attempt retry with exponential backoff
- provider/model/version accessors

Update settings with:

- `jina_api_key`
- `embedding_model`
- `embedding_version`
- `embedding_batch_size`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_jina_embedding_client.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/adapters/embedding/base.py src/image_vector_search/adapters/embedding/jina.py src/image_vector_search/config.py tests/unit/test_jina_embedding_client.py
git commit -m "feat: add embedding adapter abstraction"
```

### Task 5: Add Vector Index Abstraction With Milvus Lite

**Files:**
- Create: `src/image_vector_search/adapters/vector_index/base.py`
- Create: `src/image_vector_search/adapters/vector_index/milvus_lite.py`
- Create: `tests/unit/test_milvus_lite_index.py`
- Modify: `src/image_vector_search/config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from image_vector_search.adapters.vector_index.milvus_lite import MilvusLiteIndex


def test_milvus_lite_index_creates_collection(tmp_path: Path):
    index = MilvusLiteIndex(db_path=tmp_path / "milvus.db", collection_name="image_embeddings")
    index.ensure_collection(dimension=3, embedding_key="jina:jina-clip-v2:2026-03")
    assert index.count("jina:jina-clip-v2:2026-03") == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_milvus_lite_index.py -v`
Expected: FAIL because vector index adapter files do not exist

**Step 3: Write minimal implementation**

```python
from abc import ABC, abstractmethod


class VectorIndex(ABC):
    @abstractmethod
    def ensure_collection(self, dimension: int, embedding_key: str) -> None: ...

    @abstractmethod
    def upsert_embeddings(self, records: list[dict]) -> None: ...

    @abstractmethod
    def search(self, vector: list[float], limit: int, embedding_key: str) -> list[dict]: ...
```

```python
from pymilvus import MilvusClient


class MilvusLiteIndex:
    def __init__(self, db_path, collection_name: str) -> None:
        self.client = MilvusClient(str(db_path))
        self.collection_name = collection_name
```

Implement:

- collection creation with COSINE metric
- primary key = `content_hash`
- metadata fields for provider/model/version
- upsert semantics by `content_hash`
- `has_embedding`, `search`, and `count`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_milvus_lite_index.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/adapters/vector_index/base.py src/image_vector_search/adapters/vector_index/milvus_lite.py src/image_vector_search/config.py tests/unit/test_milvus_lite_index.py
git commit -m "feat: add milvus lite vector index adapter"
```

### Task 6: Build File Scanning And Image Metadata Utilities

**Files:**
- Create: `src/image_vector_search/scanning/files.py`
- Create: `src/image_vector_search/scanning/hashing.py`
- Create: `src/image_vector_search/scanning/image_metadata.py`
- Create: `tests/unit/test_scanning.py`

**Step 1: Write the failing test**

```python
from pathlib import Path

from image_vector_search.scanning.files import is_supported_image
from image_vector_search.scanning.hashing import sha256_file


def test_supported_image_extensions():
    assert is_supported_image(Path("a.jpg"))
    assert is_supported_image(Path("b.png"))
    assert not is_supported_image(Path("c.txt"))


def test_sha256_file_is_stable(tmp_path: Path):
    sample = tmp_path / "a.txt"
    sample.write_text("abc")
    assert sha256_file(sample) == sha256_file(sample)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_scanning.py -v`
Expected: FAIL because scanning helpers do not exist

**Step 3: Write minimal implementation**

```python
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}


def is_supported_image(path):
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
```

```python
import hashlib


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

Add:

- recursive directory scanner rooted at `images_root`
- image metadata loader using Pillow
- MIME type derivation
- container-path conversion helper

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_scanning.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/scanning/files.py src/image_vector_search/scanning/hashing.py src/image_vector_search/scanning/image_metadata.py tests/unit/test_scanning.py
git commit -m "feat: add filesystem scanning helpers"
```

### Task 7: Implement IndexService For Incremental Update And Rebuild

**Files:**
- Create: `src/image_vector_search/services/indexing.py`
- Create: `tests/integration/test_indexing_service.py`
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Modify: `src/image_vector_search/domain/models.py`

**Step 1: Write the failing test**

```python
def test_incremental_update_reuses_embedding_on_rename(service, image_factory):
    original = image_factory("2024/a.jpg", color="red")
    service.run_incremental_update()

    renamed = image_factory("2024/renamed.jpg", color="red", source=original)
    original.unlink()

    report = service.run_incremental_update()

    assert report.added == 0
    assert report.reused == 1
    assert report.path_updated >= 1
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_indexing_service.py -v`
Expected: FAIL because `IndexService` does not exist

**Step 3: Write minimal implementation**

```python
class IndexService:
    def __init__(self, settings, repository, embedding_client, vector_index) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_client = embedding_client
        self.vector_index = vector_index

    def run_incremental_update(self):
        ...

    def run_full_rebuild(self):
        ...
```

Implement the real flow with:

- path scan
- path-level `mtime/file_size` diffing
- `content_hash` reuse
- metadata insert/update
- inactive path marking
- inactive image marking
- status timestamps
- summary counters (`scanned`, `added`, `reused`, `path_updated`, `deactivated`, `skipped`, `errors`)

Use a fake embedding client in tests so no network call is needed.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_indexing_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/services/indexing.py src/image_vector_search/repositories/sqlite.py src/image_vector_search/domain/models.py tests/integration/test_indexing_service.py
git commit -m "feat: implement indexing service"
```

### Task 8: Implement SearchService With Folder Filtering And Oversampling

**Files:**
- Create: `src/image_vector_search/services/search.py`
- Create: `tests/unit/test_search_service.py`
- Modify: `src/image_vector_search/domain/models.py`

**Step 1: Write the failing test**

```python
import pytest


@pytest.mark.asyncio
async def test_search_images_oversamples_before_folder_filter(service):
    results = await service.search_images(
        query="sunset beach",
        folder="/data/images/2024",
        top_k=2,
        min_score=0.2,
    )
    assert len(results) == 2
    assert all(item.path.startswith("/data/images/2024") for item in results)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_search_service.py -v`
Expected: FAIL because `SearchService` does not exist

**Step 3: Write minimal implementation**

```python
class SearchService:
    def __init__(self, settings, repository, embedding_client, vector_index) -> None:
        self.settings = settings
        self.repository = repository
        self.embedding_client = embedding_client
        self.vector_index = vector_index

    async def search_images(self, query: str, folder: str | None, top_k: int, min_score: float):
        ...
```

Implement:

- text search
- image-path search
- folder normalization
- candidate oversampling (`top_k * 5`, floor 20, cap 200)
- `min_score` filtering
- self-match exclusion by `content_hash`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_search_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/services/search.py src/image_vector_search/domain/models.py tests/unit/test_search_service.py
git commit -m "feat: implement search service"
```

### Task 9: Expose Search Through MCP Tools

**Files:**
- Create: `src/image_vector_search/mcp/server.py`
- Create: `tests/integration/test_mcp_tools.py`
- Modify: `src/image_vector_search/app.py`

**Step 1: Write the failing test**

```python
import pytest
from fastmcp import Client


@pytest.mark.asyncio
async def test_search_images_tool_returns_structured_results(mcp_server):
    async with Client(mcp_server) as client:
        result = await client.call_tool(
            "search_images",
            {"query": "red flower", "top_k": 1},
        )
    assert result.data[0]["content_hash"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_mcp_tools.py -v`
Expected: FAIL because MCP server is not wired

**Step 3: Write minimal implementation**

```python
from fastmcp import FastMCP


def build_mcp_server(search_service) -> FastMCP:
    mcp = FastMCP("image-search-mcp")

    @mcp.tool
    async def search_images(query: str, top_k: int = 5, min_score: float = 0.0, folder: str | None = None):
        return await search_service.search_images(query=query, top_k=top_k, min_score=min_score, folder=folder)

    return mcp
```

Also add `search_similar`, then mount the MCP ASGI app under `/mcp` from the main FastAPI application.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_mcp_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/mcp/server.py src/image_vector_search/app.py tests/integration/test_mcp_tools.py
git commit -m "feat: expose search tools via mcp"
```

### Task 10: Implement Job Worker And StatusService

**Files:**
- Create: `src/image_vector_search/services/status.py`
- Create: `src/image_vector_search/services/jobs.py`
- Create: `tests/unit/test_job_runner.py`
- Modify: `src/image_vector_search/repositories/sqlite.py`

**Step 1: Write the failing test**

```python
def test_job_runner_serializes_index_jobs(job_runner, repository):
    first = job_runner.enqueue("incremental")
    second = job_runner.enqueue("full_rebuild")

    assert first.status == "queued"
    assert second.status == "queued"

    job_runner.run_next()
    job_runner.run_next()

    jobs = repository.list_recent_jobs(limit=2)
    assert [job.status for job in jobs] == ["succeeded", "succeeded"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_job_runner.py -v`
Expected: FAIL because jobs service does not exist

**Step 3: Write minimal implementation**

```python
from collections import deque


class JobRunner:
    def __init__(self, repository, index_service) -> None:
        self.repository = repository
        self.index_service = index_service
        self._queue = deque()
```

Implement:

- enqueue method
- single-running-job guard
- transition tracking (`queued` -> `running` -> `succeeded` / `failed`)
- status aggregation service for the admin page

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_job_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/services/status.py src/image_vector_search/services/jobs.py src/image_vector_search/repositories/sqlite.py tests/unit/test_job_runner.py
git commit -m "feat: add job runner and status service"
```

### Task 11: Add Admin HTTP API And Management Page

**Files:**
- Create: `src/image_vector_search/frontend/routes.py`
- Create: `src/image_vector_search/frontend/templates/index.html`
- Create: `src/image_vector_search/frontend/static/app.js`
- Create: `src/image_vector_search/frontend/static/styles.css`
- Create: `tests/integration/test_web_admin.py`
- Modify: `src/image_vector_search/app.py`

**Step 1: Write the failing test**

```python
def test_admin_home_shows_status_and_actions(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Incremental Update" in response.text
    assert "Full Rebuild" in response.text
    assert "Debug Search" in response.text
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_web_admin.py -v`
Expected: FAIL because the admin routes and template do not exist

**Step 3: Write minimal implementation**

```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter()
templates = Jinja2Templates(directory="src/image_vector_search/frontend/templates")


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

Expand it with:

- `GET /api/status`
- `POST /api/jobs/incremental`
- `POST /api/jobs/rebuild`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/debug/search/text`
- `POST /api/debug/search/similar`

Render one page with four sections:

- index status
- index actions
- job history
- debug search

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_web_admin.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/image_vector_search/frontend/routes.py src/image_vector_search/frontend/templates/index.html src/image_vector_search/frontend/static/app.js src/image_vector_search/frontend/static/styles.css src/image_vector_search/app.py tests/integration/test_web_admin.py
git commit -m "feat: add admin web interface"
```

### Task 12: Add End-To-End Tests For Search And Index Lifecycle

**Files:**
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_end_to_end_search.py`
- Modify: `tests/integration/test_indexing_service.py`
- Modify: `tests/integration/test_web_admin.py`

**Step 1: Write the failing test**

```python
def test_end_to_end_incremental_then_search(client, fake_embedding_backend, image_factory):
    image_factory("2024/sunset.jpg", color="orange")
    create = client.post("/api/jobs/incremental")
    assert create.status_code == 202

    drain_job_queue(client)

    response = client.post("/api/debug/search/text", json={"query": "orange sunset", "top_k": 1})
    body = response.json()
    assert body["results"][0]["path"] == "/data/images/2024/sunset.jpg"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_end_to_end_search.py -v`
Expected: FAIL because fixtures and cross-layer wiring are incomplete

**Step 3: Write minimal implementation**

Add integration fixtures for:

- temporary `images_root`
- temporary SQLite file
- temporary Milvus Lite file
- fake embedding client that emits deterministic vectors
- helper that drains the in-process job queue

Expand assertions to cover:

- duplicate file collapse to one content hash
- rename reuses old embedding
- deleted file becomes inactive
- MCP and debug search both return the active canonical path

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_end_to_end_search.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/integration/conftest.py tests/integration/test_end_to_end_search.py tests/integration/test_indexing_service.py tests/integration/test_web_admin.py
git commit -m "test: add end-to-end coverage"
```

### Task 13: Add Containerization And GHCR Publishing

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `.github/workflows/publish.yml`
- Create: `README.md`
- Create: `tests/unit/test_readme.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_readme_mentions_required_environment_variables():
    readme = Path("README.md").read_text()
    assert "JINA_API_KEY" in readme
    assert "/data/images" in readme
    assert "/data/index" in readme
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_readme.py -v`
Expected: FAIL because deployment artifacts are missing

**Step 3: Write minimal implementation**

Use:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

CMD ["uvicorn", "image_vector_search.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

Add `docker-compose.yml` with:

- service name `image-search-mcp`
- `/data/images` read-only mount
- `/data/index` read-write mount
- environment variables for Jina and defaults

Add GitHub Actions workflow that:

- runs `python -m pytest`
- builds Docker image
- logs into `ghcr.io`
- tags with commit SHA and `latest`
- pushes on `main`

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/test_readme.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore .github/workflows/publish.yml README.md tests/unit/test_readme.py
git commit -m "chore: add container and publish pipeline"
```

### Task 14: Run Full Verification Before Claiming Completion

**Files:**
- Modify: `README.md`
- Modify: any files needed from prior tasks after fixes

**Step 1: Write the failing test**

No new test file. Use the full suite as the gate.

**Step 2: Run test to verify current gaps**

Run: `python -m pytest -v`
Expected: identify any remaining failures or flaky assumptions

**Step 3: Write minimal implementation**

Fix only the failures found in the full suite. Keep the patch focused:

- configuration gaps
- async wiring bugs
- template/static path issues
- Milvus collection boot order
- job queue edge cases

**Step 4: Run verification to verify it passes**

Run: `python -m pytest -v`
Expected: PASS

Run: `python -m compileall src`
Expected: PASS

Run: `docker build -t image-search-mcp:test .`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md src tests Dockerfile docker-compose.yml .github/workflows/publish.yml
git commit -m "chore: verify image search service"
```

## Execution Notes

- Execute this plan with `superpowers:executing-plans`.
- Before claiming success, also apply `superpowers:verification-before-completion`.
- Use fake embedding adapters in tests; do not call Jina from the test suite.
- Keep the embedding adapter isolated. Any search or indexing code that reaches into Jina-specific request payloads is a design bug.
- Keep MCP limited to `search_images` and `search_similar`; indexing and rebuild belong to the web/admin surface only.
