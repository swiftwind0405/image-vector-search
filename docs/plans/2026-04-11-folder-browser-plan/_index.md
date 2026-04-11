# Folder Browser — Implementation Plan

**Design**: [../2026-04-11-folder-browser-design/_index.md](../2026-04-11-folder-browser-design/_index.md)
**Date**: 2026-04-11
**Owner**: Stanley

## Goal

Deliver the Folder Browser admin page exactly as specified by the design folder: a new `/folders` route that drills down through the indexed archive's directory tree, showing immediate subfolders and direct-child images at each level, with image-click behavior identical to the existing Images page.

## Scope

**In scope**
- New repository method `MetadataRepository.list_images_in_folder` (direct-child SQL predicate).
- New backend endpoint `GET /api/folders/browse` returning `{path, parent, folders, images, next_cursor}`.
- New backend router module wired into `app.py` alongside the other admin routers.
- New frontend React Query hook `useFolderBrowse`.
- New frontend page `FoldersPage` with breadcrumbs, subfolder grid, and image grid (reusing `GalleryGrid`/`ImageModal`).
- New frontend route `/folders` and a "Folders" entry in the sidebar nav.
- Tests at unit (repository), integration (HTTP endpoint), and frontend (component) levels driven by the design's BDD scenarios.

**Out of scope** (explicitly YAGNI per design)
- Folder counts, cover thumbnails on folder cards.
- Recursive "include descendants" toggle (users can still use `/images?folder=<path>` which is recursive).
- Folder rename/move/delete operations.
- Filesystem-watch live updates.
- New database indexes or migrations.
- Changes to `/api/folders`, `/api/images`, or bulk-folder routes.

## Constraints

- Test-first (Red → Green) for every feature. Verification tasks run the BDD specs.
- External dependencies (SQLite, HTTP client, React Query fetch) use the existing test-double / temp-DB / fetch-mock patterns already in the repo — do not introduce new mocking frameworks.
- Path handling in the new endpoint must reject traversal attempts (`..`, backslash, absolute paths beyond root) before touching SQL.
- SQL `LIKE` prefix must escape `%`, `_`, `\` to avoid false matches on folder names containing those characters.
- Existing tests must remain green after each impl task.
- Reuse existing frontend components (`GalleryCard`, `GalleryGrid`, `ImageModal`, `ImageInfoPanel`, `ErrorBoundary`) — do not duplicate image-rendering logic.

## Execution Plan

```yaml
tasks:
  - id: "001-test"
    subject: "list_images_in_folder repository tests"
    slug: "list-images-in-folder-test"
    type: "test"
    depends-on: []
  - id: "001-impl"
    subject: "list_images_in_folder repository impl"
    slug: "list-images-in-folder-impl"
    type: "impl"
    depends-on: ["001-test"]
  - id: "002-test"
    subject: "/api/folders/browse integration tests"
    slug: "folder-browse-endpoint-test"
    type: "test"
    depends-on: ["001-impl"]
  - id: "002-impl"
    subject: "/api/folders/browse router + app wiring"
    slug: "folder-browse-endpoint-impl"
    type: "impl"
    depends-on: ["002-test"]
  - id: "003-test"
    subject: "FoldersPage frontend tests"
    slug: "folders-page-test"
    type: "test"
    depends-on: []
  - id: "003-impl"
    subject: "FoldersPage + route + nav + API client"
    slug: "folders-page-impl"
    type: "impl"
    depends-on: ["003-test", "002-impl"]
```

## Task File References

- [Task 001 test — list_images_in_folder (Red)](./task-001-list-images-in-folder-test.md)
- [Task 001 impl — list_images_in_folder (Green)](./task-001-list-images-in-folder-impl.md)
- [Task 002 test — /api/folders/browse (Red)](./task-002-folder-browse-endpoint-test.md)
- [Task 002 impl — /api/folders/browse (Green)](./task-002-folder-browse-endpoint-impl.md)
- [Task 003 test — FoldersPage (Red)](./task-003-folders-page-test.md)
- [Task 003 impl — FoldersPage (Green)](./task-003-folders-page-impl.md)

## Dependency Chain

```
001-test ──► 001-impl ──► 002-test ──► 002-impl ─┐
                                                  ├─► 003-impl
                               003-test ─────────┘
```

Notes:
- `003-test` has no dependency on backend work — it mocks `/api/folders/browse` at the network boundary, so it can be written in parallel with any earlier task.
- `003-impl` depends on `003-test` (Red-before-Green for the frontend) **and** `002-impl` (so the manual smoke step can exercise the real backend).
- There are no cycles; every arrow points forward in task order.
- Feature 001 and feature 003 tests are independent and can run in parallel. Feature 002 tests need `001-impl` because the route under test imports the repository method that `001-impl` adds.

## BDD Coverage

Source scenarios live in [../2026-04-11-folder-browser-design/bdd-specs.md](../2026-04-11-folder-browser-design/bdd-specs.md).

| BDD Scenario (from design) | Covered by task |
|---|---|
| Repository: Direct-only query excludes nested images | 001-test / 001-impl |
| Repository: Root listing returns images directly under images_root | 001-test / 001-impl |
| Repository: Cursor pagination returns stable ordering | 001-test / 001-impl |
| Repository: (additional) Inactive images excluded | 001-test / 001-impl |
| Repository: (additional) Empty/non-matching folder returns [] | 001-test / 001-impl |
| Backend: Root-level browse returns top-level folders and root-level images | 002-test / 002-impl |
| Backend: Mid-level browse returns only immediate subfolders and direct images | 002-test / 002-impl |
| Backend: Leaf folder returns no subfolders | 002-test / 002-impl |
| Backend: Non-existent folder returns empty result (not 404) | 002-test / 002-impl |
| Backend: Path traversal attempt is rejected | 002-test / 002-impl |
| Backend: Absolute path is rejected | 002-test / 002-impl |
| Backend: Leading and trailing slashes are normalized | 002-test / 002-impl |
| Backend: Inactive images are excluded | 002-test / 002-impl |
| Backend: Images in deeper subfolders do not leak into the parent view | 002-test / 002-impl |
| Backend: Authentication is required | 002-test / 002-impl |
| Frontend: Root page renders subfolder cards and direct images | 003-test / 003-impl |
| Frontend: Clicking a subfolder drills down | 003-test / 003-impl |
| Frontend: Breadcrumb navigation jumps back up the tree | 003-test / 003-impl |
| Frontend: Image click opens the shared ImageModal | 003-test / 003-impl |
| Frontend: Empty folder shows empty state | 003-test / 003-impl |
| Frontend: Browser back returns to the previous folder | Covered implicitly by drill-down + deep-link scenarios in 003-test (MemoryRouter history assertions) |
| Frontend: Deep link loads the correct folder | 003-test / 003-impl |

Every scenario from `bdd-specs.md` is claimed by at least one task.
