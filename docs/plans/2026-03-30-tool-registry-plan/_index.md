# Tool Registry Implementation Plan

**Design**: [../2026-03-30-tool-registry-design/](./../2026-03-30-tool-registry-design/)

## Goal

Implement a central Tool Registry with decorator-based registration, auto-generated MCP and HTTP adapters, and an OpenClaw skill package. Replace the hand-written MCP server with registry-driven generation.

## Constraints

- All existing tests must continue to pass (no regressions)
- Existing admin HTTP routes (`/api/images`, `/api/tags`, etc.) remain unchanged
- MCP endpoint at `/mcp` continues to work with same protocol
- ~9 task-oriented tools covering all agent-facing operations

## Execution Plan

```yaml
tasks:
  - id: "001"
    subject: "Tool Registry Core — Tests"
    slug: "registry-core-test"
    type: "test"
    depends-on: []
  - id: "001"
    subject: "Tool Registry Core — Implementation"
    slug: "registry-core-impl"
    type: "impl"
    depends-on: ["001-registry-core-test"]
  - id: "002"
    subject: "Search Tools — Tests"
    slug: "search-tools-test"
    type: "test"
    depends-on: ["001-registry-core-impl"]
  - id: "002"
    subject: "Search Tools — Implementation"
    slug: "search-tools-impl"
    type: "impl"
    depends-on: ["002-search-tools-test"]
  - id: "003"
    subject: "Tag & Category Tools — Tests"
    slug: "tag-tools-test"
    type: "test"
    depends-on: ["001-registry-core-impl"]
  - id: "003"
    subject: "Tag & Category Tools — Implementation"
    slug: "tag-tools-impl"
    type: "impl"
    depends-on: ["003-tag-tools-test"]
  - id: "004"
    subject: "Index & Image Tools — Tests"
    slug: "index-tools-test"
    type: "test"
    depends-on: ["001-registry-core-impl"]
  - id: "004"
    subject: "Index & Image Tools — Implementation"
    slug: "index-tools-impl"
    type: "impl"
    depends-on: ["004-index-tools-test"]
  - id: "005"
    subject: "MCP Adapter — Tests"
    slug: "mcp-adapter-test"
    type: "test"
    depends-on: ["001-registry-core-impl"]
  - id: "005"
    subject: "MCP Adapter — Implementation"
    slug: "mcp-adapter-impl"
    type: "impl"
    depends-on: ["005-mcp-adapter-test"]
  - id: "006"
    subject: "HTTP Tool Adapter — Tests"
    slug: "http-adapter-test"
    type: "test"
    depends-on: ["001-registry-core-impl"]
  - id: "006"
    subject: "HTTP Tool Adapter — Implementation"
    slug: "http-adapter-impl"
    type: "impl"
    depends-on: ["006-http-adapter-test"]
  - id: "007"
    subject: "App Integration — Wire Registry into app.py"
    slug: "app-integration"
    type: "impl"
    depends-on: ["002-search-tools-impl", "003-tag-tools-impl", "004-index-tools-impl", "005-mcp-adapter-impl", "006-http-adapter-impl"]
  - id: "008"
    subject: "OpenClaw Skill Package"
    slug: "openclaw-skill"
    type: "impl"
    depends-on: ["007-app-integration"]
  - id: "009"
    subject: "Integration Tests"
    slug: "integration-test"
    type: "test"
    depends-on: ["007-app-integration"]
```

## Dependency Chain

```
001-test ──► 001-impl ──┬──► 002-test ──► 002-impl ──┐
                        ├──► 003-test ──► 003-impl ──┤
                        ├──► 004-test ──► 004-impl ──┤
                        ├──► 005-test ──► 005-impl ──┼──► 007-integration ──┬──► 008-openclaw
                        └──► 006-test ──► 006-impl ──┘                     └──► 009-integ-test
```

**Parallelism**: After 001-impl completes, tasks 002/003/004/005/006 (test+impl pairs) can all run in parallel — they are independent. Task 007 is the convergence point.

## Task File References

- [Task 001: Registry Core — Test](./task-001-registry-core-test.md)
- [Task 001: Registry Core — Impl](./task-001-registry-core-impl.md)
- [Task 002: Search Tools — Test](./task-002-search-tools-test.md)
- [Task 002: Search Tools — Impl](./task-002-search-tools-impl.md)
- [Task 003: Tag & Category Tools — Test](./task-003-tag-tools-test.md)
- [Task 003: Tag & Category Tools — Impl](./task-003-tag-tools-impl.md)
- [Task 004: Index & Image Tools — Test](./task-004-index-tools-test.md)
- [Task 004: Index & Image Tools — Impl](./task-004-index-tools-impl.md)
- [Task 005: MCP Adapter — Test](./task-005-mcp-adapter-test.md)
- [Task 005: MCP Adapter — Impl](./task-005-mcp-adapter-impl.md)
- [Task 006: HTTP Tool Adapter — Test](./task-006-http-adapter-test.md)
- [Task 006: HTTP Tool Adapter — Impl](./task-006-http-adapter-impl.md)
- [Task 007: App Integration](./task-007-app-integration.md)
- [Task 008: OpenClaw Skill Package](./task-008-openclaw-skill.md)
- [Task 009: Integration Tests](./task-009-integration-test.md)

## BDD Coverage

| BDD Feature | Scenarios | Covered By |
|---|---|---|
| Tool Registry | Register, Schema inference (3), List, Get | 001-test |
| Tool Execution | Search (2), Tags create/list/error (4) | 002-test, 003-test |
| Tool Execution | Index status, trigger, list images, image info | 004-test |
| MCP Adapter | Generate server, invocation, error, schema match | 005-test |
| HTTP Tool Adapter | Discovery, invoke, 404, error mapping (2) | 006-test |
| OpenClaw Integration | Discovery, search, end-to-end tags | 008, 009-test |

All 22 BDD scenarios from the design are covered.
