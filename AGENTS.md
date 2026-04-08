# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

Image vector search service. Indexes local images using Jina embeddings, stores vectors in Milvus Lite, and exposes semantic search via HTTP API and HTTP tool endpoints. Agents can search images by text description or find visually similar images.

## Commands

```bash
# Install (use virtual environment)
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/unit/test_search_service.py

# Run a single test by name
pytest -k "test_name"

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Start the server locally (listens on 0.0.0.0:8000, supports LAN access)
python -m image_vector_search
```

## Architecture

**Source layout**: `src/image_vector_search/` — single Python package with `src` layout (`pyproject.toml` sets `package-dir = src`).

**Key architectural decisions**:
- Content-hash identity: images are identified by SHA-256 of file contents, not file paths. Path changes don't trigger re-embedding.
- Dual storage: SQLite for metadata/state (`MetadataRepository`), Milvus Lite for vector embeddings (`MilvusLiteIndex`).
- All services are constructed via `runtime.build_runtime_services()` factory, which returns a `RuntimeServices` dataclass. This is the dependency injection point.
- Fully async (FastAPI + uvicorn). Background indexing uses a single-threaded `BackgroundJobWorker` with an async queue.

**Component map**:
- `app.py` — FastAPI application factory with lifespan. Serves admin UI and HTTP APIs.
- `config.py` — `Settings` via pydantic-settings. Env var prefix: `IMAGE_SEARCH_`. Key vars: `jina_api_key`, `images_root`, `index_root`.
- `runtime.py` — Bootstraps all services from config.
- `services/` — `SearchService`, `IndexService`, `JobRunner`, `StatusService`, `BackgroundJobWorker`.
- `adapters/` — `JinaEmbeddingClient` (HTTP to Jina API), `MilvusLiteIndex` (vector DB). Both have abstract base classes.
- `repositories/` — `MetadataRepository` (SQLite).
- `scanning/` — File hashing, image metadata extraction (PIL), path normalization.
- `web/` — Admin console routes, templates, static assets.

**Testing**: pytest with pytest-asyncio for async tests, respx for HTTP mocking. Unit tests mock adapters; integration tests use `conftest.py` fixtures that wire up real services with temp directories.

## Docker

```bash
docker compose up --build    # dev/test
# Production: published to ghcr.io via .github/workflows/publish.yml on push to main/master
```

Container mounts: `/data/images` (read-only source), `/data/index` (read-write persistence).

## Subagent Cost Policy

- Use Explore agent (Haiku) or custom `researcher` agent for file search and codebase exploration
- Use Haiku model for any research-only subagents
- Reserve Opus for implementation, debugging, and complex reasoning
