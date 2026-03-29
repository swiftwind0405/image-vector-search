---
name: image-search
description: Search images by text description or find visually similar images via HTTP API
---

# Image Search

Search the local indexed image library via HTTP API. Supports two modes:

1. **Text search** — describe what you're looking for in natural language
2. **Similar search** — provide a reference image path to find visually similar images

## Prerequisites

The image-search-mcp server must be running and images must be indexed.

```bash
cd /Users/stanley/Workspace/main/image-vector-search
python -m image_search_mcp
```

Server base URL: `http://localhost:8000`

## API Endpoints

### 1. Text Search — `POST /api/debug/search/text`

Search images by natural language description.

**Request body (JSON):**

| Field       | Type             | Required | Default | Description                                      |
|-------------|------------------|----------|---------|--------------------------------------------------|
| `query`     | `string`         | Yes      | —       | Natural language description of the desired image |
| `top_k`     | `int`            | No       | `5`     | Number of results to return (≥ 1)                 |
| `min_score` | `float`          | No       | `0.0`   | Minimum similarity score threshold                |
| `folder`    | `string \| null` | No       | `null`  | Restrict to images under this folder path         |

**Example:**

```bash
curl -X POST http://localhost:8000/api/debug/search/text \
  -H "Content-Type: application/json" \
  -d '{"query": "sunset over the ocean", "top_k": 5}'
```

---

### 2. Similar Image Search — `POST /api/debug/search/similar`

Find images visually similar to a reference image. The reference image **must already be indexed**.

**Request body (JSON):**

| Field        | Type             | Required | Default | Description                                       |
|--------------|------------------|----------|---------|---------------------------------------------------|
| `image_path` | `string`         | Yes      | —       | Absolute file path to the reference image          |
| `top_k`      | `int`            | No       | `5`     | Number of similar images to return (≥ 1)           |
| `min_score`  | `float`          | No       | `0.0`   | Minimum similarity score threshold                 |
| `folder`     | `string \| null` | No       | `null`  | Restrict to images under this folder path          |

**Example:**

```bash
curl -X POST http://localhost:8000/api/debug/search/similar \
  -H "Content-Type: application/json" \
  -d '{"image_path": "/data/images/photos/beach.jpg", "top_k": 10, "min_score": 0.5}'
```

**Error responses:**
- `404` — image_path file not found on disk
- `400` — reference image has not been indexed yet

---

## Response Format

Both endpoints return the same structure:

```json
{
  "results": [
    {
      "content_hash": "sha256...",
      "path": "/data/images/photos/sunset.jpg",
      "score": 0.82,
      "width": 1920,
      "height": 1080,
      "mime_type": "image/jpeg",
      "tags": [{"id": 1, "name": "landscape"}],
      "categories": [{"id": 2, "name": "nature"}]
    }
  ]
}
```

| Field          | Type     | Description                                |
|----------------|----------|--------------------------------------------|
| `content_hash` | `string` | SHA-256 hash identifying the image content |
| `path`         | `string` | File path of the matched image             |
| `score`        | `float`  | Similarity score (higher = more relevant)  |
| `width`        | `int`    | Image width in pixels                      |
| `height`       | `int`    | Image height in pixels                     |
| `mime_type`    | `string` | MIME type (e.g. `image/jpeg`)              |
| `tags`         | `array`  | Associated tags                            |
| `categories`   | `array`  | Associated categories                      |

## Related Endpoints

| Method | Path                                  | Description              |
|--------|---------------------------------------|--------------------------|
| `GET`  | `/api/images/{content_hash}/file`     | Download the full image  |
| `GET`  | `/api/images/{content_hash}/thumbnail?size=120` | Get a JPEG thumbnail |
| `GET`  | `/api/status`                         | Index status and stats   |

## Tips

- Use descriptive phrases rather than single keywords for text search
- Set `min_score` to `0.2`–`0.3` to filter out low-confidence matches
- For similar search, the reference image itself is automatically excluded from results
- Images must be indexed before they appear in search results — trigger indexing via `POST /api/jobs/incremental`
