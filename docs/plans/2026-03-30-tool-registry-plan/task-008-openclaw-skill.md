# Task 008: OpenClaw Skill Package

**depends-on**: ["007-app-integration"]
**type**: impl
**files**:
- `openclaw-skill/SKILL.md` (create)

## Description

Create an OpenClaw skill that documents how agents can use the image search service via HTTP API.

### `openclaw-skill/SKILL.md`
- Frontmatter: name, description, user-invocable: true, metadata with primaryEnv: IMAGE_SEARCH_URL
- Body sections:
  - **Configuration**: How to set `IMAGE_SEARCH_URL`
  - **Tool Discovery**: Reference to `GET $IMAGE_SEARCH_URL/api/tools`
  - **Usage Examples**: curl examples for common operations (search, tag management, index status)
  - **Available Tools**: Brief description of each tool with its purpose

## BDD Scenario

```gherkin
Scenario: OpenClaw agent discovers tools
  Given the image-search server is running at $IMAGE_SEARCH_URL
  When an OpenClaw agent fetches GET $IMAGE_SEARCH_URL/api/tools
  Then it receives a list of available tools with schemas
  And can determine which tool to call based on descriptions

Scenario: OpenClaw agent searches images
  Given the image-search server has indexed images
  When an OpenClaw agent POSTs to /api/tools/search_images
    with body {"query": "red flowers in garden", "top_k": 3}
  Then it receives results with image paths and similarity scores

Scenario: OpenClaw agent manages tags end-to-end
  Given the image-search server is running
  When an OpenClaw agent:
    1. POSTs /api/tools/manage_tags with {"action": "create", "name": "vacation"}
    2. POSTs /api/tools/search_images with {"query": "beach sunset"}
    3. POSTs /api/tools/tag_images with {"action": "add_tag", "content_hash": "<hash>", "tag_id": 1}
  Then the image is tagged with "vacation"
```

## Verification

- Verify SKILL.md has valid YAML frontmatter (parseable)
- Verify all curl examples reference correct endpoint paths that exist in the registry
- Manual: install skill in OpenClaw and verify tool discovery works
