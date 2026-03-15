# Image Search MCP

Local image semantic search service with two operator surfaces:

- MCP tools for agents: `search_images`, `search_similar`
- Admin web console for status, indexing jobs, and debug search

The service stores image metadata in SQLite and embeddings in a local Milvus Lite database. Image paths are always container paths, with `/data/images` mounted read-only and `/data/index` mounted read-write.

## Requirements

- Python 3.12+
- A `JINA_API_KEY` with access to Jina embeddings
- A mounted image library at `/data/images`
- A writable index directory at `/data/index`

## Environment Variables

Required:

- `IMAGE_SEARCH_JINA_API_KEY`

Optional:

- `IMAGE_SEARCH_IMAGES_ROOT`
- `IMAGE_SEARCH_INDEX_ROOT`
- `IMAGE_SEARCH_HOST`
- `IMAGE_SEARCH_PORT`
- `IMAGE_SEARCH_DEFAULT_TOP_K`
- `IMAGE_SEARCH_MAX_TOP_K`
- `IMAGE_SEARCH_MIN_SCORE`
- `IMAGE_SEARCH_EMBEDDING_PROVIDER`
- `IMAGE_SEARCH_EMBEDDING_MODEL`
- `IMAGE_SEARCH_EMBEDDING_VERSION`
- `IMAGE_SEARCH_VECTOR_INDEX_COLLECTION_NAME`
- `IMAGE_SEARCH_VECTOR_INDEX_DB_FILENAME`

Default mount paths:

- images: `/data/images`
- index: `/data/index`

## Local Development

Create a virtualenv, install dependencies, then run the test suite:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest tests -v
```

Run the application:

```bash
uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

## Docker

Build:

```bash
docker build -t image-search-mcp:test .
```

Run with Docker Compose:

```bash
export IMAGE_SEARCH_JINA_API_KEY=your-key
docker compose up --build
```

The compose example exposes:

- admin console: `http://localhost:8000/`
- MCP transport mount: `http://localhost:8000/mcp`

## Operator Surface

Admin HTTP routes:

- `GET /`
- `GET /api/status`
- `POST /api/jobs/incremental`
- `POST /api/jobs/rebuild`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/debug/search/text`
- `POST /api/debug/search/similar`

MCP tools:

- `search_images`
- `search_similar`

## Persistence

The service keeps:

- SQLite metadata at `/data/index/metadata.db`
- Milvus Lite vectors at `/data/index/milvus.db`

Back up `/data/index` to preserve job history, metadata, and vectors.
