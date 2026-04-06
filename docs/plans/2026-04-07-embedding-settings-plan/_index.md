# Plan: Embedding Settings Admin UI

**Date:** 2026-04-07  
**Design:** [docs/plans/2026-04-07-embedding-settings-admin-ui-design/](../2026-04-07-embedding-settings-admin-ui-design/_index.md)  
**Status:** Ready for execution

## Goal

Move `IMAGE_SEARCH_EMBEDDING_PROVIDER` and API keys (Jina/Google) from environment variables into the admin UI. Store in SQLite `system_state`. Hot-reload embedding client on save (no restart).

## Constraints

- No DB schema changes — reuse `system_state` table
- API keys never returned in plaintext
- Backward compat: env var fallback if no DB config
- Scope: only `provider` + `jina_api_key` + `google_api_key`

## Execution Plan

```yaml
tasks:
  - id: "001"
    subject: "Repository embedding config tests"
    slug: "repo-embedding-config-test"
    type: "test"
    depends-on: []
  - id: "002"
    subject: "Repository embedding config impl"
    slug: "repo-embedding-config-impl"
    type: "impl"
    depends-on: ["001"]
  - id: "003"
    subject: "RuntimeServices hot-reload tests"
    slug: "runtime-reload-test"
    type: "test"
    depends-on: ["002"]
  - id: "004"
    subject: "RuntimeServices hot-reload impl"
    slug: "runtime-reload-impl"
    type: "impl"
    depends-on: ["003"]
  - id: "005"
    subject: "Settings API endpoint tests"
    slug: "settings-api-test"
    type: "test"
    depends-on: ["004"]
  - id: "006"
    subject: "Settings API endpoint impl"
    slug: "settings-api-impl"
    type: "impl"
    depends-on: ["005"]
  - id: "007"
    subject: "Frontend settings API client impl"
    slug: "frontend-settings-client-impl"
    type: "impl"
    depends-on: ["006"]
  - id: "008"
    subject: "SettingsPage component tests"
    slug: "settings-page-test"
    type: "test"
    depends-on: ["007"]
  - id: "009"
    subject: "SettingsPage component impl"
    slug: "settings-page-impl"
    type: "impl"
    depends-on: ["008"]
  - id: "010"
    subject: "Frontend routing and navigation impl"
    slug: "frontend-routing-impl"
    type: "impl"
    depends-on: ["009"]
```

## Task File References

- [Task 001: Repository embedding config tests](./task-001-repo-embedding-config-test.md)
- [Task 002: Repository embedding config impl](./task-002-repo-embedding-config-impl.md)
- [Task 003: RuntimeServices hot-reload tests](./task-003-runtime-reload-test.md)
- [Task 004: RuntimeServices hot-reload impl](./task-004-runtime-reload-impl.md)
- [Task 005: Settings API endpoint tests](./task-005-settings-api-test.md)
- [Task 006: Settings API endpoint impl](./task-006-settings-api-impl.md)
- [Task 007: Frontend settings API client impl](./task-007-frontend-settings-client-impl.md)
- [Task 008: SettingsPage component tests](./task-008-settings-page-test.md)
- [Task 009: SettingsPage component impl](./task-009-settings-page-impl.md)
- [Task 010: Frontend routing and navigation impl](./task-010-frontend-routing-impl.md)

## BDD Coverage

| Scenario | Tasks |
|----------|-------|
| S1: View masked config | 005, 008 |
| S2: Save happy path | 005, 008, 009 |
| S3a: Provider switch (key exists) | 005 |
| S3b: Provider switch (key missing) | 005, 008 |
| S4: Invalid provider 422 | 005 |
| S5: Reload failure 500 | 003, 005, 008 |
| S6: Fresh install no config | 003, 005, 008 |
| S7: Env var fallback startup | 003, 005, 008 |
| S8: Dirty-state handling | 008 |
| Repo: get/set embedding config | 001, 002 |

## Dependency Chain

```
001 (repo test)
 └─▶ 002 (repo impl)
       └─▶ 003 (runtime test)
             └─▶ 004 (runtime impl)
                   └─▶ 005 (api test)
                         └─▶ 006 (api impl)
                               └─▶ 007 (frontend client)
                                     └─▶ 008 (page test)
                                           └─▶ 009 (page impl)
                                                 └─▶ 010 (routing)
```
