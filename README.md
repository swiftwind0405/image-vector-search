# Image Vector Search

Local image semantic search service with a FastAPI backend, browser-based admin console, and HTTP tool endpoints for agent integration.

## What It Does

- Indexes local images under a configured root directory
- Generates multimodal embeddings with either Jina or Gemini
- Stores image metadata in SQLite and vectors in Milvus Lite
- Supports text-to-image search and image-to-image similarity search
- Provides admin workflows for indexing, status inspection, tagging, categories, and bulk labeling

## Operator Surfaces

- Admin UI: `/`
- Health check: `/healthz`
- HTTP tool discovery: `GET /api/tools`
- HTTP tool invocation: `POST /api/tools/{tool_name}`
- Admin/search APIs: `/api/*`

## Quick Start

### 1. Prepare the environment

```bash
cp .env.example .env
mkdir -p ./data/images ./data/config
```

Put sample images into `./data/images` or point `IMAGE_SEARCH_IMAGES_ROOT` to your own directory.

### 2. Install dependencies

Using `uv`:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Using standard `venv`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

### 3. Start the service

```bash
python -m image_vector_search
```

The app binds to `0.0.0.0:8000` by default and is typically reachable at `http://localhost:8000`.

## Configuration Model

Configuration is split across two layers:

- Environment variables: filesystem paths, server settings, embedding defaults, auth, vector index settings
- Admin settings page: persisted embedding provider and API keys stored in SQLite

Embedding resolution order:

1. Provider/API key saved through `/settings`
2. Environment variable fallback
3. If neither is configured, the app still starts but embedding-backed search/indexing remains unavailable

This means `.env` can be used for bootstrap or headless deployment, while the admin UI can later persist provider/key changes without editing environment files.

## Key Environment Variables

Required for actual embedding requests:

- `IMAGE_SEARCH_JINA_API_KEY` when provider is `jina`
- `IMAGE_SEARCH_GOOGLE_API_KEY` when provider is `gemini`

Common settings:

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
- `IMAGE_SEARCH_GEMINI_BASE_URL`
- `IMAGE_SEARCH_EMBEDDING_OUTPUT_DIMENSIONALITY`
- `IMAGE_SEARCH_EMBEDDING_BATCH_SIZE`
- `IMAGE_SEARCH_JINA_RPM`
- `IMAGE_SEARCH_JINA_MAX_CONCURRENCY`
- `IMAGE_SEARCH_VECTOR_INDEX_COLLECTION_NAME`
- `IMAGE_SEARCH_VECTOR_INDEX_DB_FILENAME`
- `IMAGE_SEARCH_ADMIN_USERNAME`
- `IMAGE_SEARCH_ADMIN_PASSWORD`
- `IMAGE_SEARCH_ADMIN_SESSION_SECRET`

See [.env.example](.env.example) for a full template.

## Local Development

Run tests:

```bash
pytest
```

Run only unit tests:

```bash
pytest tests/unit/
```

Run the frontend in dev mode:

```bash
cd src/image_vector_search/frontend
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and proxies `/api` to the backend.

## Search and Indexing Workflow

Typical flow:

1. Start the app
2. Configure embedding provider/key through `.env` or `/settings`
3. Trigger `POST /api/jobs/incremental` or `POST /api/jobs/rebuild`
4. Inspect `GET /api/status`
5. Search through the admin UI or `/api/tools/search_images`

## Docker

Build the image:

```bash
docker build -t image-vector-search:test .
```

Run with Compose:

```bash
docker compose up --build
```

If you want search to work immediately after container startup, provide a provider key through `.env` or exported shell variables before launch. If no key is present, the app still starts and can be configured later through the admin settings page.

Default container paths:

- images root: `/data/images`
- index root: `/data/config`

The repository now ignores large local frontend and Python caches during Docker builds, which keeps the build context smaller and avoids sending local `node_modules`, `.venv`, and other transient artifacts into the image build.

## Release Process

Container publishing is driven by Git tags pushed to GitHub Actions.

Current workflow behavior:

- Pushing branches alone does not publish an image
- Pushing a tag that matches `v*.*.*` triggers `.github/workflows/docker.yml`
- Publishing a GitHub Release in the web UI does not trigger the container build by itself

Typical release flow:

```bash
git checkout master
git pull
pytest
git tag v0.1.0
git push origin master
git push origin v0.1.0
```

After the tag is pushed, GitHub Actions builds and publishes the container image to `ghcr.io/<owner>/<repo>`.

## Persistence

Files stored under `IMAGE_SEARCH_INDEX_ROOT`:

- `metadata.db`: SQLite metadata, jobs, saved embedding settings
- `milvus.db`: Milvus Lite vector data

Back up the entire index directory if you want to preserve search state.

## Related Docs

- Usage guide: [docs/usage.md](docs/usage.md)
- API guide: [docs/api.md](docs/api.md)
