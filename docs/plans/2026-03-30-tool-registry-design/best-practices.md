# Best Practices and Considerations

## Security

### Path Sanitization
Tools that accept file paths (`search_similar`, `list_images` with folder filter) must validate paths stay within `images_root`:

```python
def validate_path(path: str, images_root: Path) -> Path:
    resolved = (images_root / path).resolve()
    if not resolved.is_relative_to(images_root.resolve()):
        raise ValueError(f"Path escapes images root: {path}")
    return resolved
```

Apply this in tool handlers, not in adapters (defense in depth — services also validate, but tools are the first boundary).

### HTTP Tool Endpoint Authentication
The `/api/tools/*` endpoints should respect the same auth middleware as existing admin routes. If `admin_username` and `admin_password` are configured, require authentication for tool invocation.

For OpenClaw integration, support API key authentication via `Authorization: Bearer <key>` header as an alternative to session-based auth.

### Input Validation
- `action` parameters are validated by `Literal` type constraints
- Bulk operations enforce `MAX_BULK_SIZE = 500` at the tool handler level
- String inputs are stripped and validated for emptiness where appropriate
- Integer IDs are validated as positive

### No SQL Injection Risk
All database access goes through `MetadataRepository` which uses parameterized queries. Tools never construct SQL directly.

## Performance

### Schema Caching
JSON Schemas are generated once at registration time (during import), not per-request. The `ToolDef.input_schema` is computed in the `@registry.tool` decorator and stored.

### Async Consistency
All tool handlers are `async def`. Services that are synchronous (TagService, IndexService) are called directly (they don't block the event loop for significant time since they're SQLite operations). If a service operation is expected to take >100ms, wrap in `asyncio.to_thread()`.

### Tool Discovery Caching
The `GET /api/tools` response is static (tools don't change at runtime). Add `Cache-Control: public, max-age=3600` header.

## Code Quality

### Tool Handler Conventions
1. First parameter is always `ctx: ToolContext`
2. Return type is always `dict` (for consistent JSON serialization)
3. Use `Literal` for action parameters, not free-form strings
4. Validate required parameter combinations and raise `ValueError` with clear messages
5. Keep handlers thin — delegate to services, don't add business logic

### Action Parameter Validation Pattern
```python
@registry.tool(name="manage_tags")
async def manage_tags(
    ctx: ToolContext,
    action: Literal["create", "rename", "delete", "list"],
    name: str | None = None,
    tag_id: int | None = None,
    new_name: str | None = None,
) -> dict:
    if action == "create":
        if not name:
            raise ValueError("'name' is required for action 'create'")
        tag = ctx.tag_service.create_tag(name)
        return {"tag": tag.model_dump()}
    elif action == "rename":
        if tag_id is None or not new_name:
            raise ValueError("'tag_id' and 'new_name' are required for action 'rename'")
        ctx.tag_service.rename_tag(tag_id, new_name)
        return {"ok": True}
    # ...
```

### Testing Conventions
- Unit test each tool with a fake `ToolContext`
- Test each `action` variant separately
- Test error cases (missing params, invalid values)
- Integration tests go through the HTTP adapter with real services

## OpenClaw Specific

### Skill Documentation
The SKILL.md should include:
- Clear description of what the service does
- `IMAGE_SEARCH_URL` environment variable for server location
- Example curl commands for common operations
- Reference to `GET /api/tools` for full tool discovery

### Response Format
Tools return plain dicts. For OpenClaw compatibility, keep responses simple and flat where possible. Avoid deeply nested structures that are hard for agents to parse.

### Error Messages
Error messages should be descriptive enough for an agent to self-correct:
- Bad: `"Invalid input"`
- Good: `"'name' is required when action is 'create'. Provide a non-empty string."`

## Future Considerations

### A2A Protocol Support
The Tool Registry is designed to support future A2A integration. An A2A adapter would:
1. Read tool definitions from the registry
2. Generate an Agent Card (`.well-known/agent.json`) listing capabilities
3. Map incoming A2A task requests to tool invocations

### OpenAPI Spec Generation
The HTTP tool adapter can generate an OpenAPI spec from the registry. Each tool becomes a `POST /api/tools/{name}` operation with the tool's input_schema as the request body schema.

### Versioning
Tools are not versioned in this initial design. If breaking changes are needed later, add version prefixes: `/api/v2/tools/{name}`.
