# Image Search MCP

Local image semantic search service with two operator surfaces:

- MCP tools for agents: `search_images`, `search_similar`
- Admin web console for status, indexing jobs, and debug search

The service stores image metadata in SQLite and embeddings in a local Milvus Lite database. Image paths are always container paths, with `/data/images` mounted read-only and `/data/index` mounted read-write.

## Requirements

- Python 3.12+ (or use [uv](https://docs.astral.sh/uv/) for automatic management)
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

### Using uv (recommended)

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest tests -v
```

### Traditional method

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest tests -v
```

Run the application:

### Backend Server

#### Using uv (recommended)

First, create a `.env` file and directories:

```bash
cp .env.example .env
# Edit .env with your actual values
mkdir -p ./data/images ./data/index
```

Then run with environment file:

```bash
uv run --env-file .env uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

Or export variables manually:

```bash
export IMAGE_SEARCH_IMAGES_ROOT=./data/images
export IMAGE_SEARCH_INDEX_ROOT=./data/index
export IMAGE_SEARCH_JINA_API_KEY=your_api_key_here
uv run uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

#### Traditional method

```bash
source .venv/bin/activate
export IMAGE_SEARCH_IMAGES_ROOT=./data/images
export IMAGE_SEARCH_INDEX_ROOT=./data/index
export IMAGE_SEARCH_JINA_API_KEY=your_api_key_here
uvicorn image_search_mcp.app:create_app --factory --host 0.0.0.0 --port 8000
```

Server runs at `http://localhost:8000/` (serves static React frontend) and `/mcp` for MCP protocol.

### Frontend Development (React)

For development with hot reload:

```bash
cd src/image_search_mcp/web
npm install
npm run dev
```

Vite dev server runs at `http://localhost:5173/` and proxies `/api/*` to `http://localhost:8000`.

To build for production:

```bash
cd src/image_search_mcp/web
npm run build
```

Build output goes to `dist/` (served by FastAPI in production).

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