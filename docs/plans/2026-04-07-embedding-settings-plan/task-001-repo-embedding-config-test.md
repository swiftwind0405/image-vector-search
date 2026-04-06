# Task 001: Repository Embedding Config — Tests

**type:** test  
**depends-on:** []

## Goal

Write unit tests for two new `MetadataRepository` methods: `get_embedding_config()` and `set_embedding_config()`. These methods read/write embedding provider and API key settings from the `system_state` SQLite table.

## BDD Scenario

```gherkin
Scenario: get_embedding_config returns None for unconfigured keys
  Given system_state table has no config.* rows
  When get_embedding_config() is called
  Then it returns {"provider": None, "jina_api_key": None, "google_api_key": None}

Scenario: set_embedding_config writes only specified keys
  Given system_state table is empty
  When set_embedding_config(provider="gemini") is called
  Then system_state has key "config.embedding_provider" = "gemini"
  And system_state has no "config.jina_api_key" or "config.google_api_key" rows

Scenario: set_embedding_config with None key does not overwrite existing
  Given system_state has "config.jina_api_key" = "existing-key"
  When set_embedding_config(jina_api_key=None) is called
  Then system_state still has "config.jina_api_key" = "existing-key"
  And no row is deleted or modified

Scenario: set_embedding_config overwrites when value is provided
  Given system_state has "config.jina_api_key" = "old-key"
  When set_embedding_config(jina_api_key="new-key") is called
  Then system_state has "config.jina_api_key" = "new-key"
```

## Files to Create

- `tests/unit/test_repository_embedding_config.py`

## Test Cases

1. `test_get_embedding_config_returns_none_when_empty` — call on fresh DB, assert all fields None
2. `test_get_embedding_config_returns_stored_values` — set keys manually via `set_system_state`, then call `get_embedding_config()`
3. `test_set_embedding_config_writes_only_specified_keys` — pass only `provider="jina"`, assert no jina_api_key or google_api_key written
4. `test_set_embedding_config_null_does_not_overwrite` — pre-set a key, call `set_embedding_config(jina_api_key=None)`, assert key unchanged
5. `test_set_embedding_config_overwrites_when_value_given` — pre-set a key, update it, assert new value

## Verification

```bash
pytest tests/unit/test_repository_embedding_config.py -v
```

All 5 tests must fail (Red) before implementation.
