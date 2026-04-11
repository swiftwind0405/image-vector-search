# BDD Specifications — Folder Browser

All scenarios use the Gherkin Given/When/Then style and target real integration tests wherever possible (FastAPI `TestClient` + temp images root for backend, Vitest + React Testing Library for frontend). Unit tests mock only the network boundary.

## Feature: Browse folders and direct images

### Backend — `GET /api/folders/browse`

#### Scenario: Root-level browse returns top-level folders and root-level images
```gherkin
Given the index contains images:
  | canonical_path                         |
  | /images_root/a/1.jpg                   |
  | /images_root/a/b/2.jpg                 |
  | /images_root/a/b/c/3.jpg               |
  | /images_root/top.jpg                   |
When I GET /api/folders/browse
Then the response status is 200
And response.path is ""
And response.parent is null
And response.folders is ["a"]
And response.images contains exactly the image with canonical_path "/images_root/top.jpg"
```

#### Scenario: Mid-level browse returns only immediate subfolders and direct images
```gherkin
Given the index contains images:
  | /images_root/a/1.jpg          |
  | /images_root/a/b/2.jpg        |
  | /images_root/a/b/c/3.jpg      |
  | /images_root/a/d/4.jpg        |
When I GET /api/folders/browse?path=a
Then response.path is "a"
And response.parent is ""
And response.folders is ["a/b", "a/d"]
And response.images contains exactly the image "/images_root/a/1.jpg"
```

#### Scenario: Leaf folder returns no subfolders
```gherkin
Given the index contains image /images_root/a/b/c/3.jpg
When I GET /api/folders/browse?path=a/b/c
Then response.folders is []
And response.images contains "/images_root/a/b/c/3.jpg"
```

#### Scenario: Non-existent folder returns empty result (not 404)
```gherkin
When I GET /api/folders/browse?path=does/not/exist
Then response status is 200
And response.folders is []
And response.images is []
```
(Rationale: the folder might become valid after the next indexing job; treating it as empty avoids user-visible 404s during races.)

#### Scenario: Path traversal attempt is rejected
```gherkin
When I GET /api/folders/browse?path=../etc
Then the response status is 400
And the response body contains "invalid path"
```

#### Scenario: Absolute path is rejected
```gherkin
When I GET /api/folders/browse?path=/etc/passwd
Then the response status is 400
```

#### Scenario: Leading and trailing slashes are normalized
```gherkin
Given the index contains image /images_root/a/1.jpg
When I GET /api/folders/browse?path=/a/
Then response.path is "a"
And response.images contains the image
```

#### Scenario: Inactive images are excluded
```gherkin
Given image /images_root/a/1.jpg exists but is marked is_active = 0
When I GET /api/folders/browse?path=a
Then response.images does not contain that image
```

#### Scenario: Images in deeper subfolders do not leak into the parent view
```gherkin
Given the index contains only /images_root/a/b/2.jpg
When I GET /api/folders/browse?path=a
Then response.folders is ["a/b"]
And response.images is []
```

#### Scenario: Authentication is required
```gherkin
Given no admin session cookie is set
When I GET /api/folders/browse
Then the response status is 401 or the request is redirected to /login
```
(Matches behavior of the other admin routers; verify whatever the existing admin routes return today.)

### Repository — `list_images_in_folder`

#### Scenario: Direct-only query excludes nested images
```gherkin
Given images:
  | /images_root/a/1.jpg      |
  | /images_root/a/b/2.jpg    |
When I call repository.list_images_in_folder(path="a", images_root="/images_root")
Then the result contains "/images_root/a/1.jpg"
And the result does not contain "/images_root/a/b/2.jpg"
```

#### Scenario: Root listing returns images directly under images_root
```gherkin
Given images:
  | /images_root/top.jpg      |
  | /images_root/a/1.jpg      |
When I call repository.list_images_in_folder(path="", images_root="/images_root")
Then the result contains "/images_root/top.jpg"
And the result does not contain "/images_root/a/1.jpg"
```

#### Scenario: Cursor pagination returns stable ordering
```gherkin
Given 50 images directly in /images_root/a with distinct filenames
When I call list_images_in_folder(path="a", limit=20)
And then call it again with the returned next_cursor
Then the two pages together contain all 50 images with no duplicates
And the ordering is ascending by canonical_path
```

### Frontend — `/folders` page

#### Scenario: Root page renders subfolder cards and direct images
```gherkin
Given the user is authenticated
And the browse endpoint returns folders=["a","b"] and images=[img1]
When the user navigates to /folders
Then a "Folders" entry is highlighted in the sidebar
And two folder cards labeled "a" and "b" are rendered
And one image card for img1 is rendered below the folders section
```

#### Scenario: Clicking a subfolder drills down
```gherkin
Given the /folders page is rendered with folder "a"
When the user clicks the "a" folder card
Then the URL becomes /folders?path=a
And the page refetches browse data with path="a"
```

#### Scenario: Breadcrumb navigation jumps back up the tree
```gherkin
Given the user is on /folders?path=a/b/c
Then breadcrumbs "Root / a / b / c" are visible
When the user clicks the "a" crumb
Then the URL becomes /folders?path=a
```

#### Scenario: Image click opens the shared ImageModal
```gherkin
Given /folders?path=a is rendered with one image card
When the user clicks the image card
Then ImageModal opens with that image's details
And tags/categories for that image are fetched as on the Images page
```

#### Scenario: Empty folder shows empty state
```gherkin
Given /api/folders/browse?path=a returns folders=[] and images=[]
When the user navigates to /folders?path=a
Then the page renders "This folder is empty."
```

#### Scenario: Browser back returns to the previous folder
```gherkin
Given the user navigated Root → a → a/b
When the user clicks the browser Back button
Then the URL returns to /folders?path=a
And the correct folder contents are rendered
```

#### Scenario: Deep link loads the correct folder
```gherkin
When the user opens /folders?path=a/b/c directly
Then the page renders the contents of a/b/c (no intermediate redirects)
```

## Testing Strategy

**Backend unit tests** (`tests/unit/`):
- `test_sqlite_list_images_in_folder.py` — direct SQL behavior using the existing temp-DB fixtures.
- `test_folder_routes.py` — FastAPI TestClient against `create_admin_folder_router`, with a stubbed `repository` / `status_service`.

**Backend integration tests** (`tests/integration/`):
- `test_folder_browser_api.py` — full runtime services wired up via `conftest.py` fixtures, exercising real SQLite + fake images.

**Frontend tests** (`src/image_vector_search/frontend/src/test/`):
- `FoldersPage.test.tsx` — Vitest + React Testing Library with an MSW mock of `/api/folders/browse`, covering rendering, navigation, and empty-state.

**Manual smoke**:
- Run `docker compose up --build`, populate a sample directory with nested folders, log into the admin UI, walk the tree to at least 3 levels deep, click into an image, click Back.

All scenarios above should be translated to executing tests before merging; follow `superpowers:test-driven-development` when implementing.
