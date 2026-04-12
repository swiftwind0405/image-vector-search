# Album Feature — Implementation Plan

## Goal

Implement the album feature with two album types (manual and smart) as described in the [album feature design](../2026-04-12-album-feature-design/_index.md).

## Architecture

- **Backend**: New `AlbumService` + repository methods + API routes, following existing TagService/admin_tag_routes patterns
- **Database**: 4 new SQLite tables (albums, album_images, album_rules, album_source_paths)
- **Frontend**: 2 new pages (AlbumsPage, AlbumImagesPage), API client hooks, routing

## Constraints

- Test-first (Red-Green) workflow for all backend tasks
- Follow existing codebase patterns exactly
- No modification to existing tags/categories schema
- Independent tables for albums

## Execution Plan

```yaml
tasks:
  - id: "001"
    subject: "Database Schema and Domain Models"
    slug: "schema-and-models"
    type: "setup"
    depends-on: []
  - id: "002a"
    subject: "Album CRUD Test"
    slug: "album-crud-test"
    type: "test"
    depends-on: ["001"]
  - id: "002b"
    subject: "Album CRUD Impl"
    slug: "album-crud-impl"
    type: "impl"
    depends-on: ["002a"]
  - id: "003a"
    subject: "Manual Album Image Management Test"
    slug: "manual-images-test"
    type: "test"
    depends-on: ["001"]
  - id: "003b"
    subject: "Manual Album Image Management Impl"
    slug: "manual-images-impl"
    type: "impl"
    depends-on: ["003a", "002b"]
  - id: "004a"
    subject: "Smart Album Rules and Query Test"
    slug: "smart-rules-test"
    type: "test"
    depends-on: ["001"]
  - id: "004b"
    subject: "Smart Album Rules and Query Impl"
    slug: "smart-rules-impl"
    type: "impl"
    depends-on: ["004a", "002b"]
  - id: "005a"
    subject: "Cover Image and Album Listing Test"
    slug: "cover-image-test"
    type: "test"
    depends-on: ["001"]
  - id: "005b"
    subject: "Cover Image and Album Listing Impl"
    slug: "cover-image-impl"
    type: "impl"
    depends-on: ["005a", "003b", "004b"]
  - id: "006"
    subject: "Runtime Wiring"
    slug: "runtime-wiring"
    type: "setup"
    depends-on: ["002b"]
  - id: "007a"
    subject: "Album API Routes Test"
    slug: "api-test"
    type: "test"
    depends-on: ["006"]
  - id: "007b"
    subject: "Album API Routes Impl"
    slug: "api-impl"
    type: "impl"
    depends-on: ["007a", "005b"]
  - id: "008"
    subject: "Frontend API Client and Types"
    slug: "frontend-api"
    type: "impl"
    depends-on: ["007b"]
  - id: "009"
    subject: "Frontend Pages and Routing"
    slug: "frontend-pages"
    type: "impl"
    depends-on: ["008"]
```

## Task File References

- [Task 001: Database Schema and Domain Models](./task-001-schema-and-models.md)
- [Task 002: Album CRUD Test](./task-002-album-crud-test.md)
- [Task 002: Album CRUD Impl](./task-002-album-crud-impl.md)
- [Task 003: Manual Album Image Management Test](./task-003-manual-images-test.md)
- [Task 003: Manual Album Image Management Impl](./task-003-manual-images-impl.md)
- [Task 004: Smart Album Rules and Query Test](./task-004-smart-rules-test.md)
- [Task 004: Smart Album Rules and Query Impl](./task-004-smart-rules-impl.md)
- [Task 005: Cover Image and Album Listing Test](./task-005-cover-image-test.md)
- [Task 005: Cover Image and Album Listing Impl](./task-005-cover-image-impl.md)
- [Task 006: Runtime Wiring](./task-006-runtime-wiring.md)
- [Task 007: Album API Routes Test](./task-007-api-test.md)
- [Task 007: Album API Routes Impl](./task-007-api-impl.md)
- [Task 008: Frontend API Client and Types](./task-008-frontend-api.md)
- [Task 009: Frontend Pages and Routing](./task-009-frontend-pages.md)

## BDD Coverage

All 40 BDD scenarios from the design are covered:

| Feature | Scenarios | Tasks |
|---------|-----------|-------|
| Album CRUD | 7 scenarios | 002 |
| Manual Album Image Management | 6 scenarios | 003 |
| Manual Album Pagination | 1 scenario | 003 |
| Smart Album Rules | 8 scenarios | 004 |
| Cover Image | 3 scenarios | 005 |
| Smart Album Source Paths | 5 scenarios | 004 |
| Smart Album Edge Cases | 4 scenarios | 004 |
| Smart Album Pagination | 1 scenario | 004 |
| Error Handling | 4 scenarios | 002, 003, 004, 007 |
| Album Listing | 1 scenario | 005 |

## Dependency Chain

```
001 Schema & Models
├── 002-test Album CRUD Test
│   └── 002-impl Album CRUD Impl
│       ├── 003-impl Manual Images Impl
│       ├── 004-impl Smart Rules Impl
│       └── 006 Runtime Wiring
│           └── 007-test API Test
├── 003-test Manual Images Test
├── 004-test Smart Rules Test
└── 005-test Cover Image Test

003-impl + 004-impl
└── 005-impl Cover Image Impl
    └── 007-impl API Impl
        └── 008 Frontend API
            └── 009 Frontend Pages
```

### Parallelizable Groups

After task 001 completes, the following can run in parallel:
- **Group A**: 002-test, 003-test, 004-test, 005-test (all test tasks are independent)
- **Group B** (after their test): 002-impl, then 003-impl + 004-impl + 006 in parallel
- **Group C** (after 003-impl + 004-impl): 005-impl
- **Group D** (sequential): 007-test → 007-impl → 008 → 009
