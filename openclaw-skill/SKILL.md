---
name: image-search
description: Search images by text description, find visually similar images, and manage tags using the image-search service
user-invocable: true
metadata:
  primaryEnv: IMAGE_SEARCH_URL
---

# Image Search Skill

Provides semantic image search and tag management via the image-search HTTP API.

## Configuration

Set the IMAGE_SEARCH_URL environment variable to the base URL of your image-search server:

export IMAGE_SEARCH_URL=http://localhost:8000

## Tool Discovery

Fetch available tools and their schemas:

curl $IMAGE_SEARCH_URL/api/tools

## Available Tools

| Tool | Description |
|------|-------------|
| search_images | Search images by text description using semantic similarity |
| search_similar | Find images visually similar to a given image |
| manage_tags | Create, rename, delete, or list image tags |
| manage_categories | Create, rename, delete, move, or list image categories |
| tag_images | Add or remove tags/categories from images |
| list_images | List indexed images with optional folder/tag/category filter |
| get_image_info | Get metadata, tags, and categories for a specific image |
| get_index_status | Get current index statistics and recent job history |
| trigger_index | Trigger an indexing job (incremental or full_rebuild) |

## Usage Examples

### Search images

curl -X POST $IMAGE_SEARCH_URL/api/tools/search_images -H 'Content-Type: application/json' -d '{"query": "red flowers in garden", "top_k": 3}'

### Get index status

curl -X POST $IMAGE_SEARCH_URL/api/tools/get_index_status -H 'Content-Type: application/json' -d '{}'

### Create a tag

curl -X POST $IMAGE_SEARCH_URL/api/tools/manage_tags -H 'Content-Type: application/json' -d '{"action": "create", "name": "vacation"}'

### Tag an image

curl -X POST $IMAGE_SEARCH_URL/api/tools/tag_images -H 'Content-Type: application/json' -d '{"action": "add_tag", "content_hash": "<hash>", "tag_id": 1}'

### Trigger incremental index

curl -X POST $IMAGE_SEARCH_URL/api/tools/trigger_index -H 'Content-Type: application/json' -d '{"mode": "incremental"}'
