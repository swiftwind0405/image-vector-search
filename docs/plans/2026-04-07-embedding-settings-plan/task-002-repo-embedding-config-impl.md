# Task 002: Repository Embedding Config — Implementation

**type:** impl  
**depends-on:** ["001"]

## Goal

Add `get_embedding_config()` and `set_embedding_config()` methods to `MetadataRepository` in `src/image_search_mcp/repositories/sqlite.py`.

## BDD Scenario

```gherkin
Scenario: get_embedding_config returns None for unconfigured keys
  Given system_state table has no config.* rows
  When get_embedding_config() is called
  Then it returns {"provider": None, "jina_api_key": None, "google_api_key": None}

Scenario: set_embedding_config with None key does not overwrite existing
  Given system_state has "config.jina_api_key" = "existing-key"
  When set_embedding_config(jina_api_key=None) is called
  Then system_state still has "config.jina_api_key" = "existing-key"
```

## Files to Modify

- `src/image_search_mcp/repositories/sqlite.py`

## What to Implement

Add two methods to `MetadataRepository`:

**`get_embedding_config() -> dict[str, str | None]`**
- Reads three keys from `system_state`: `config.embedding_provider`, `config.jina_api_key`, `config.google_api_key`
- Returns a dict with keys `"provider"`, `"jina_api_key"`, `"google_api_key"` — `None` if the key is absent
- Uses existing `get_system_state()` internally

**`set_embedding_config(*, provider=None, jina_api_key=None, google_api_key=None) -> None`**
- Only writes a value when the parameter is not `None` (keyword-only, all default to `None`)
- Uses existing `set_system_state()` internally
- Writes to: `config.embedding_provider`, `config.jina_api_key`, `config.google_api_key`

DB key constants (define at module level or as class attributes):
- `"config.embedding_provider"`
- `"config.jina_api_key"`
- `"config.google_api_key"`

## Verification

```bash
pytest tests/unit/test_repository_embedding_config.py -v
```

All 5 tests must pass (Green).
