# Task 006: Runtime Wiring

**type**: setup
**depends-on**: [002-album-crud-impl]

## Goal

Wire `AlbumService` into the runtime dependency injection system so it's available to API routes.

## Files to Modify

- `src/image_vector_search/runtime.py` — Add `album_service: AlbumService` to `RuntimeServices` dataclass, initialize in `build_runtime_services()`

## What to Implement

1. Import `AlbumService` from `services.albums`
2. Add `album_service: AlbumService` field to `RuntimeServices` dataclass
3. In `build_runtime_services()`, create `AlbumService(repository=repository)` and pass it to `RuntimeServices`

## Verification

```bash
python -c "
from image_vector_search.runtime import RuntimeServices
import inspect
assert 'album_service' in [f.name for f in inspect.fields(RuntimeServices) if hasattr(inspect, 'fields')]
print('Wiring OK')
"

# Also run existing tests to ensure no regressions
pytest tests/unit/ -v --timeout=30
```
