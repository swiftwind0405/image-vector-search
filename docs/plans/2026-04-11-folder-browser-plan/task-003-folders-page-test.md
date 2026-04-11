# Task 003 — Folders page (Red)

**type**: test
**feature**: folders-page
**depends-on**: []

## Objective

Add failing frontend tests for a new `/folders` route rendering a `FoldersPage` that:
- Fetches `/api/folders/browse?path=<path>` via a React Query hook.
- Renders breadcrumbs, a subfolder grid, and an image grid.
- Drills down when a folder card is clicked, opens the shared `ImageModal` when an image is clicked.
- Handles empty and loading states.

The page, route, API client, and sidebar nav entry must not yet exist — tests must fail until Task 003 impl lands. No backend dependency: the tests mock `/api/folders/browse` at the fetch boundary.

## Files

- **Create**: `src/image_vector_search/frontend/src/test/FoldersPage.test.tsx`
- **Read / imitate**: existing frontend tests under `src/image_vector_search/frontend/src/test/` for the setup idiom (Vitest, React Testing Library, any MSW or fetch-mock helper the project already uses, React Query `QueryClientProvider` wrapping).
- **Do not touch**: `App.tsx`, `Layout.tsx`, `pages/`, `api/folders.ts` (those are the Green step).

## BDD Scenarios

```gherkin
Scenario: Root page renders subfolder cards and direct images
  Given the user is authenticated
  And GET /api/folders/browse returns:
    { path: "", parent: null, folders: ["a","b"], images: [img1] }
  When the user navigates to /folders
  Then the page renders folder cards labeled "a" and "b"
  And renders one image card for img1 below the folders section

Scenario: Clicking a subfolder drills down
  Given the /folders page is rendered with folder "a" in its response
  When the user clicks the "a" folder card
  Then the URL becomes /folders?path=a
  And a new request is made to /api/folders/browse?path=a

Scenario: Breadcrumb navigation jumps back up the tree
  Given the user is on /folders?path=a/b/c
  Then breadcrumb segments "Root", "a", "b", "c" are visible
  When the user clicks the "a" crumb
  Then the URL becomes /folders?path=a

Scenario: Image click opens the shared ImageModal
  Given /folders?path=a is rendered with one image
  When the user clicks that image card
  Then an ImageModal (or a modal with role="dialog" containing image details) is visible

Scenario: Empty folder shows empty state
  Given GET /api/folders/browse?path=a returns folders=[] and images=[]
  When the user navigates to /folders?path=a
  Then the page renders a "This folder is empty." message

Scenario: Deep link loads the correct folder
  When the user opens /folders?path=a/b/c directly
  Then a request is made with path=a/b/c
  And the returned contents are rendered
```

## Steps

1. Inspect an existing frontend test (e.g., any `*.test.tsx` under `frontend/src/test/`) to learn the setup pattern: router wrapper, QueryClient provider, fetch mock / MSW handler, any helper that renders the authenticated app shell.
2. Create `FoldersPage.test.tsx`:
   - Import the yet-to-exist `FoldersPage` (the test file must reference `@/pages/FoldersPage` or whichever path the impl will use — confirm by reading other page test imports).
   - For each scenario, mock `/api/folders/browse` with the appropriate response using the project's existing mock style.
   - Use `MemoryRouter` / `createMemoryRouter` with the desired `initialEntries` to target `/folders` or `/folders?path=...`.
   - Assert on DOM (`screen.getByText("a")`, `findByRole("dialog")`, etc.) and on history changes (assert `window.location` or use `useLocation` spy).
3. Each test must fail because the import does not resolve or the component does not exist. Do not create any source files to make them compile — failure is expected.

## Verification

- `npm --prefix src/image_vector_search/frontend test -- FoldersPage` — every test fails (Red).
- The failure is due to missing module / missing component, not an unrelated syntax error.
- Other frontend tests continue to pass: `npm --prefix src/image_vector_search/frontend test` — only the new file fails.

## Out of scope

- Writing the page or API client (Task 003 impl).
- Backend changes.
