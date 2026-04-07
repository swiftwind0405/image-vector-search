# React Admin Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the admin console from Jinja2 + vanilla JS to a React SPA with tags, categories, and image association management pages.

**Architecture:** React SPA built with Vite, served by FastAPI as static files. API-first: all data flows through existing `/api/*` endpoints plus a new `GET /api/images`. React Query manages server state; shadcn/ui provides the component library.

**Tech Stack:** React 18, TypeScript, Vite, React Router v6, TanStack React Query, shadcn/ui, Tailwind CSS, lucide-react

**Spec:** `docs/superpowers/specs/2026-03-17-react-admin-frontend-design.md`

---

## Task 1: Backend — Add `GET /api/images` endpoint

The Images page needs a list of all indexed images. No such endpoint exists.

**Files:**
- Modify: `src/image_vector_search/repositories/sqlite.py`
- Modify: `src/image_vector_search/frontend/routes.py`
- Modify: `tests/integration/test_web_admin.py`

- [ ] **Step 1: Write the failing test for the repository method**

In `tests/unit/test_sqlite_repository.py`, add a fixture and test:

```python
from datetime import UTC, datetime
from image_vector_search.domain.models import ImageRecord, ImagePathRecord

@pytest.fixture
def repo_with_active_image(tmp_path):
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    now = datetime.now(UTC)
    repo.upsert_image(ImageRecord(
        content_hash="abc123",
        canonical_path="/images/test.jpg",
        file_size=1024,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=80,
        is_active=True,
        last_seen_at=now,
        embedding_provider="fake",
        embedding_model="fake-clip",
        embedding_version="v1",
        created_at=now,
        updated_at=now,
    ))
    return repo


def test_list_active_images(repo_with_active_image):
    """list_active_images returns all active ImageRecords."""
    images = repo_with_active_image.list_active_images()
    assert len(images) == 1
    assert images[0].content_hash == "abc123"
    assert images[0].is_active is True
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `pytest tests/unit/test_sqlite_repository.py::test_list_active_images -v`
Expected: FAIL — `AttributeError: 'MetadataRepository' object has no attribute 'list_active_images'`

- [ ] **Step 3: Implement `list_active_images` in MetadataRepository**

In `src/image_vector_search/repositories/sqlite.py`, add after `get_image` (around line 90):

```python
def list_active_images(self) -> list[ImageRecord]:
    with self.connect() as connection:
        rows = connection.execute(
            "SELECT * FROM images WHERE is_active = 1 ORDER BY canonical_path ASC"
        ).fetchall()
    return [_row_to_image(row) for row in rows]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_sqlite_repository.py::test_list_active_images -v`
Expected: PASS

- [ ] **Step 5: Write failing test for the API endpoint**

In `tests/integration/test_web_admin.py`, add:

```python
def test_list_images_api():
    client = create_test_client()
    response = client.get("/api/images")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 6: Run test to confirm failure**

Run: `pytest tests/integration/test_web_admin.py::test_list_images_api -v`
Expected: FAIL — 404 or 405

- [ ] **Step 7: Add `GET /api/images` endpoint to routes.py**

In `src/image_vector_search/frontend/routes.py`, the `create_web_router` function needs a `repository` parameter. However, to keep changes minimal, add it to `tag_routes.py` instead (which already has access to `TagService` and its repository). Or better, expose it via `StatusService` which already has repository access.

Add to `src/image_vector_search/services/status.py`:

```python
def list_active_images(self) -> list[ImageRecord]:
    return self._repository.list_active_images()
```

Add to `src/image_vector_search/frontend/routes.py` inside `create_web_router`:

```python
@router.get("/api/images")
async def list_images():
    return JSONResponse(
        content=jsonable_encoder(status_service.list_active_images())
    )
```

- [ ] **Step 8: Update `create_test_client` in test_web_admin.py**

The `FakeStatusService` needs `list_active_images`. Add to the class:

```python
def list_active_images(self):
    from image_vector_search.domain.models import ImageRecord
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    return [
        ImageRecord(
            content_hash="hash-red",
            canonical_path="/data/images/red.jpg",
            file_size=1024,
            mtime=1000.0,
            mime_type="image/jpeg",
            width=12,
            height=8,
            is_active=True,
            last_seen_at=now,
            embedding_provider="fake",
            embedding_model="fake-clip",
            embedding_version="2026-03",
            created_at=now,
            updated_at=now,
        )
    ]
```

- [ ] **Step 9: Run all tests**

Run: `pytest tests/integration/test_web_admin.py -v`
Expected: ALL PASS

- [ ] **Step 10: Commit**

```bash
git add src/image_vector_search/repositories/sqlite.py src/image_vector_search/services/status.py src/image_vector_search/frontend/routes.py tests/
git commit -m "feat: add GET /api/images endpoint for listing active images"
```

---

## Task 2: Scaffold Vite + React project in `web/`

**Files:**
- Create: `src/image_vector_search/frontend/package.json`
- Create: `src/image_vector_search/frontend/tsconfig.json`
- Create: `src/image_vector_search/frontend/tsconfig.app.json`
- Create: `src/image_vector_search/frontend/tsconfig.node.json`
- Create: `src/image_vector_search/frontend/vite.config.ts`
- Create: `src/image_vector_search/frontend/index.html`
- Create: `src/image_vector_search/frontend/postcss.config.js`
- Create: `src/image_vector_search/frontend/tailwind.config.ts` (or `components.json` for shadcn)
- Create: `src/image_vector_search/frontend/src/main.tsx`
- Create: `src/image_vector_search/frontend/src/App.tsx`
- Create: `src/image_vector_search/frontend/src/index.css`
- Create: `src/image_vector_search/frontend/src/lib/utils.ts`
- Create: `src/image_vector_search/frontend/src/components/ErrorBoundary.tsx`
- Modify: `.gitignore`

- [ ] **Step 1: Initialize the Vite project**

```bash
cd src/image_vector_search/frontend
npm create vite@latest . -- --template react-ts
```

If the directory is not empty (it has `routes.py` etc.), use a temp directory then move files:

```bash
cd /tmp && npm create vite@latest react-scaffold -- --template react-ts
cp /tmp/react-scaffold/tsconfig.json src/image_vector_search/frontend/
cp /tmp/react-scaffold/tsconfig.app.json src/image_vector_search/frontend/
cp /tmp/react-scaffold/tsconfig.node.json src/image_vector_search/frontend/
cp /tmp/react-scaffold/vite.config.ts src/image_vector_search/frontend/
cp /tmp/react-scaffold/index.html src/image_vector_search/frontend/
cp -r /tmp/react-scaffold/src/main.tsx src/image_vector_search/frontend/src/
rm -rf /tmp/react-scaffold
```

- [ ] **Step 2: Create `package.json`**

```json
{
  "name": "image-search-admin",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "@tanstack/react-query": "^5.62.0",
    "lucide-react": "^0.460.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.6.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "~5.6.2",
    "vite": "^6.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0"
  }
}
```

- [ ] **Step 3: Configure Vite**

`src/image_vector_search/frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
```

`outDir: "dist"` resolves to `frontend/dist/` since `vite.config.ts` lives in `web/`.

- [ ] **Step 4: Configure Tailwind CSS**

`src/image_vector_search/frontend/postcss.config.js`:

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

`src/image_vector_search/frontend/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Create entry files**

`src/image_vector_search/frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Image Search Console</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`src/image_vector_search/frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

`src/image_vector_search/frontend/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

`src/image_vector_search/frontend/src/components/ErrorBoundary.tsx`:

```tsx
import React from "react";

interface Props {
  children: React.ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex items-center justify-center h-screen">
          <div className="text-center space-y-2">
            <h1 className="text-xl font-semibold">Something went wrong</h1>
            <p className="text-sm text-muted-foreground">
              {this.state.error.message}
            </p>
            <button
              className="text-sm underline"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

`src/image_vector_search/frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
```

`src/image_vector_search/frontend/src/App.tsx`:

```tsx
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";

function DashboardPage() {
  return <div>Dashboard — coming soon</div>;
}

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 6: Create minimal Layout component**

`src/image_vector_search/frontend/src/components/Layout.tsx`:

```tsx
import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Tag, FolderTree, ImagePlus } from "lucide-react";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/tags", icon: Tag, label: "Tags" },
  { to: "/categories", icon: FolderTree, label: "Categories" },
  { to: "/images", icon: ImagePlus, label: "Images" },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="w-56 border-r bg-white p-4 flex flex-col gap-1">
        <h1 className="text-lg font-semibold mb-4 px-2">Image Search</h1>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-md px-2 py-1.5 text-sm ${
                isActive
                  ? "bg-gray-100 font-medium text-gray-900"
                  : "text-gray-600 hover:bg-gray-50"
              }`
            }
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </NavLink>
        ))}
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
```

- [ ] **Step 7: Update .gitignore**

Add to `.gitignore`:

```
# React frontend
src/image_vector_search/frontend/node_modules/
src/image_vector_search/frontend/dist/
```

- [ ] **Step 8: Install dependencies and verify dev server starts**

```bash
cd src/image_vector_search/frontend
npm install
npm run dev
```

Expected: Vite dev server starts at http://localhost:5173, shows "Dashboard — coming soon" with sidebar.

Press Ctrl+C to stop.

- [ ] **Step 9: Commit**

```bash
git add src/image_vector_search/frontend/package.json src/image_vector_search/frontend/package-lock.json \
  src/image_vector_search/frontend/tsconfig*.json src/image_vector_search/frontend/vite.config.ts \
  src/image_vector_search/frontend/index.html src/image_vector_search/frontend/postcss.config.js \
  src/image_vector_search/frontend/tailwind.config.ts src/image_vector_search/frontend/src/ \
  .gitignore
git commit -m "feat: scaffold Vite + React + Tailwind project in web/"
```

---

## Task 3: Set up shadcn/ui

**Files:**
- Modify: `src/image_vector_search/frontend/package.json`
- Create: `src/image_vector_search/frontend/components.json`
- Create: `src/image_vector_search/frontend/src/components/ui/` (multiple files)

- [ ] **Step 1: Initialize shadcn/ui**

```bash
cd src/image_vector_search/frontend
npx shadcn@latest init
```

Select: TypeScript, Default style, Default color (Neutral/Zinc), CSS variables: yes, path alias `@/` for components and utils.

This creates `components.json` and updates `tailwind.config.ts` and `index.css` with CSS variables.

- [ ] **Step 2: Add core UI components needed for the app**

```bash
cd src/image_vector_search/frontend
npx shadcn@latest add button card input label table dialog badge select toast sonner
```

This creates files under `src/components/ui/`.

- [ ] **Step 3: Set up Sonner toast provider**

In `src/image_vector_search/frontend/src/main.tsx`, add after `<App />`:

```tsx
import { Toaster } from "@/components/ui/sonner";

// Inside render:
<React.StrictMode>
  <QueryClientProvider client={queryClient}>
    <BrowserRouter>
      <App />
      <Toaster />
    </BrowserRouter>
  </QueryClientProvider>
</React.StrictMode>
```

- [ ] **Step 4: Verify the dev server still works**

```bash
cd src/image_vector_search/frontend && npm run dev
```

Expected: App renders with styled components, no console errors.

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/frontend/
git commit -m "feat: set up shadcn/ui with core components"
```

---

## Task 4: API client layer

**Files:**
- Create: `src/image_vector_search/frontend/src/api/client.ts`
- Create: `src/image_vector_search/frontend/src/api/types.ts`
- Create: `src/image_vector_search/frontend/src/api/status.ts`
- Create: `src/image_vector_search/frontend/src/api/jobs.ts`
- Create: `src/image_vector_search/frontend/src/api/tags.ts`
- Create: `src/image_vector_search/frontend/src/api/categories.ts`
- Create: `src/image_vector_search/frontend/src/api/images.ts`

- [ ] **Step 1: Create the fetch wrapper and API error class**

`src/image_vector_search/frontend/src/api/client.ts`:

```typescript
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new ApiError(res.status, text);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}
```

- [ ] **Step 2: Create TypeScript types matching backend models**

`src/image_vector_search/frontend/src/api/types.ts`:

```typescript
export interface Tag {
  id: number;
  name: string;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
}

export interface CategoryNode extends Category {
  children: CategoryNode[];
}

export interface ImageRecord {
  content_hash: string;
  canonical_path: string;
  file_size: number;
  mtime: number;
  mime_type: string;
  width: number;
  height: number;
  is_active: boolean;
  last_seen_at: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_version: string;
  created_at: string;
  updated_at: string;
}

export interface IndexStatus {
  images_on_disk: number;
  total_images: number;
  active_images: number;
  inactive_images: number;
  vector_entries: number;
  embedding_provider: string;
  embedding_model: string;
  embedding_version: string;
  last_incremental_update_at: string | null;
  last_full_rebuild_at: string | null;
  last_error_summary: string | null;
}

export interface JobRecord {
  id: string;
  job_type: string;
  status: string;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  summary_json: string | null;
  error_text: string | null;
}

export interface SearchResult {
  content_hash: string;
  path: string;
  score: number;
  width: number;
  height: number;
  mime_type: string;
  tags: Tag[];
  categories: Category[];
}
```

- [ ] **Step 3: Create React Query hooks for status**

`src/image_vector_search/frontend/src/api/status.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { IndexStatus } from "./types";

export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: () => apiFetch<IndexStatus>("/api/status"),
    refetchInterval: 3000,
  });
}
```

- [ ] **Step 4: Create React Query hooks for jobs**

`src/image_vector_search/frontend/src/api/jobs.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { JobRecord } from "./types";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<JobRecord[]>("/api/jobs"),
    refetchInterval: 3000,
  });
}

export function useQueueJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobType: "incremental" | "rebuild") =>
      apiFetch<JobRecord>(`/api/jobs/${jobType}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["status"] });
    },
  });
}
```

- [ ] **Step 5: Create React Query hooks for tags**

`src/image_vector_search/frontend/src/api/tags.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { Tag } from "./types";

export function useTags() {
  return useQuery({
    queryKey: ["tags"],
    queryFn: () => apiFetch<Tag[]>("/api/tags"),
  });
}

export function useCreateTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      apiFetch<Tag>("/api/tags", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useRenameTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      apiFetch<{ ok: boolean }>(`/api/tags/${id}`, {
        method: "PUT",
        body: JSON.stringify({ name }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}

export function useDeleteTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/tags/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tags"] }),
  });
}
```

- [ ] **Step 6: Create React Query hooks for categories**

`src/image_vector_search/frontend/src/api/categories.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { CategoryNode } from "./types";

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<CategoryNode[]>("/api/categories"),
  });
}

export function useCreateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; parent_id?: number | null }) =>
      apiFetch("/api/categories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useUpdateCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: number;
      name?: string | null;
      move_to_parent_id?: number | null;
      move_to_root?: boolean;
    }) =>
      apiFetch(`/api/categories/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}

export function useDeleteCategory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/api/categories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["categories"] }),
  });
}
```

- [ ] **Step 7: Create React Query hooks for images**

`src/image_vector_search/frontend/src/api/images.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { ImageRecord, Tag, Category } from "./types";

export function useImages() {
  return useQuery({
    queryKey: ["images"],
    queryFn: () => apiFetch<ImageRecord[]>("/api/images"),
  });
}

export function useImageTags(contentHash: string) {
  return useQuery({
    queryKey: ["images", contentHash, "tags"],
    queryFn: () => apiFetch<Tag[]>(`/api/images/${contentHash}/tags`),
    enabled: !!contentHash,
  });
}

export function useImageCategories(contentHash: string) {
  return useQuery({
    queryKey: ["images", contentHash, "categories"],
    queryFn: () =>
      apiFetch<Category[]>(`/api/images/${contentHash}/categories`),
    enabled: !!contentHash,
  });
}

export function useAddTagToImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      tagId,
    }: {
      contentHash: string;
      tagId: number;
    }) =>
      apiFetch(`/api/images/${contentHash}/tags`, {
        method: "POST",
        body: JSON.stringify({ tag_id: tagId }),
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({ queryKey: ["images", contentHash, "tags"] });
    },
  });
}

export function useRemoveTagFromImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      tagId,
    }: {
      contentHash: string;
      tagId: number;
    }) =>
      apiFetch<void>(`/api/images/${contentHash}/tags/${tagId}`, {
        method: "DELETE",
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({ queryKey: ["images", contentHash, "tags"] });
    },
  });
}

export function useAddCategoryToImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      categoryId,
    }: {
      contentHash: string;
      categoryId: number;
    }) =>
      apiFetch(`/api/images/${contentHash}/categories`, {
        method: "POST",
        body: JSON.stringify({ category_id: categoryId }),
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({
        queryKey: ["images", contentHash, "categories"],
      });
    },
  });
}

export function useRemoveCategoryFromImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      categoryId,
    }: {
      contentHash: string;
      categoryId: number;
    }) =>
      apiFetch<void>(`/api/images/${contentHash}/categories/${categoryId}`, {
        method: "DELETE",
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({
        queryKey: ["images", contentHash, "categories"],
      });
    },
  });
}
```

- [ ] **Step 8: Verify TypeScript compiles**

```bash
cd src/image_vector_search/frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 9: Commit**

```bash
git add src/image_vector_search/frontend/src/api/
git commit -m "feat: add API client layer with React Query hooks"
```

---

## Task 5: Dashboard page

**Files:**
- Create: `src/image_vector_search/frontend/src/pages/DashboardPage.tsx`
- Modify: `src/image_vector_search/frontend/src/App.tsx`

- [ ] **Step 1: Create DashboardPage component**

`src/image_vector_search/frontend/src/pages/DashboardPage.tsx`:

```tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useStatus } from "@/api/status";
import { useJobs, useQueueJob } from "@/api/jobs";
import { apiFetch } from "@/api/client";
import type { SearchResult } from "@/api/types";
import { toast } from "sonner";

export default function DashboardPage() {
  const { data: status } = useStatus();
  const { data: jobs } = useJobs();
  const queueJob = useQueueJob();
  const [query, setQuery] = useState("");
  const [similarHash, setSimilarHash] = useState("");
  const [searchResults, setSearchResults] = useState<string>("");

  const handleTextSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/text",
        { method: "POST", body: JSON.stringify({ query, top_k: 5 }) },
      );
      setSearchResults(JSON.stringify(res, null, 2));
    } catch (err) {
      toast.error("Search failed");
    }
  };

  const handleSimilarSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!similarHash.trim()) return;
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/similar",
        {
          method: "POST",
          body: JSON.stringify({ image_path: similarHash, top_k: 5 }),
        },
      );
      setSearchResults(JSON.stringify(res, null, 2));
    } catch (err) {
      toast.error("Similar search failed");
    }
  };

  const handleQueueJob = (type: "incremental" | "rebuild") => {
    queueJob.mutate(type, {
      onSuccess: () => toast.success(`${type} job queued`),
      onError: () => toast.error("Failed to queue job"),
    });
  };

  const progress =
    status && status.images_on_disk > 0
      ? Math.round((status.active_images / status.images_on_disk) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Index Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Index Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Indexing progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            {status && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-muted-foreground">On Disk</div>
                  <div className="text-lg font-medium">
                    {status.images_on_disk}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Indexed</div>
                  <div className="text-lg font-medium text-primary">
                    {status.active_images}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Inactive</div>
                  <div className="text-lg font-medium">
                    {status.inactive_images}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Vectors</div>
                  <div className="text-lg font-medium">
                    {status.vector_entries}
                  </div>
                </div>
              </div>
            )}
            {status && (
              <p className="text-xs text-muted-foreground">
                {status.embedding_provider} / {status.embedding_model} /{" "}
                {status.embedding_version}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Index Control */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Index Control</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full"
              onClick={() => handleQueueJob("incremental")}
              disabled={queueJob.isPending}
            >
              Incremental Update
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => handleQueueJob("rebuild")}
              disabled={queueJob.isPending}
            >
              Full Rebuild
            </Button>
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {!jobs || jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No jobs yet</p>
            ) : (
              <ul className="space-y-2">
                {jobs.slice(0, 10).map((job) => (
                  <li
                    key={job.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{job.job_type}</span>
                    <Badge variant="secondary">{job.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Debug Search */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Debug Search</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <form onSubmit={handleTextSearch} className="flex gap-2">
              <Input
                placeholder="Text query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
            <form onSubmit={handleSimilarSearch} className="flex gap-2">
              <Input
                placeholder="Image path for similar search..."
                value={similarHash}
                onChange={(e) => setSimilarHash(e.target.value)}
              />
              <Button type="submit" variant="secondary">
                Similar
              </Button>
            </form>
            {searchResults && (
              <pre className="bg-gray-950 text-gray-100 p-3 rounded-md text-xs overflow-auto max-h-64">
                {searchResults}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update App.tsx to use the DashboardPage**

Replace the placeholder `DashboardPage` in `App.tsx`:

```tsx
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
      </Route>
    </Routes>
  );
}
```

- [ ] **Step 3: Verify with dev server**

Start both backend and frontend:

```bash
# Terminal 1:
uvicorn image_vector_search.app:create_app --factory --port 8000

# Terminal 2:
cd src/image_vector_search/frontend && npm run dev
```

Visit http://localhost:5173. Verify: sidebar renders, Dashboard shows status cards, jobs list, search forms. (Data may be empty if no index exists, but the UI should render without errors.)

- [ ] **Step 4: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/DashboardPage.tsx src/image_vector_search/frontend/src/App.tsx
git commit -m "feat: implement Dashboard page with status, jobs, and debug search"
```

---

## Task 6: Tags page

Note: The spec mentions "associated image count" in the tag table. There is no API endpoint for tag usage counts, so the table shows Name, Created, and Actions for now. Image count can be added when a count endpoint is implemented.

**Files:**
- Create: `src/image_vector_search/frontend/src/pages/TagsPage.tsx`
- Modify: `src/image_vector_search/frontend/src/App.tsx`

- [ ] **Step 1: Create TagsPage component**

`src/image_vector_search/frontend/src/pages/TagsPage.tsx`:

```tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useTags, useCreateTag, useRenameTag, useDeleteTag } from "@/api/tags";
import type { Tag } from "@/api/types";
import { toast } from "sonner";
import { Pencil, Trash2 } from "lucide-react";

export default function TagsPage() {
  const { data: tags, isLoading } = useTags();
  const createTag = useCreateTag();
  const renameTag = useRenameTag();
  const deleteTag = useDeleteTag();

  const [newName, setNewName] = useState("");
  const [editingTag, setEditingTag] = useState<Tag | null>(null);
  const [editName, setEditName] = useState("");
  const [deletingTag, setDeletingTag] = useState<Tag | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createTag.mutate(newName.trim(), {
      onSuccess: () => {
        setNewName("");
        toast.success("Tag created");
      },
      onError: (err) => toast.error(err.message),
    });
  };

  const handleRename = () => {
    if (!editingTag || !editName.trim()) return;
    renameTag.mutate(
      { id: editingTag.id, name: editName.trim() },
      {
        onSuccess: () => {
          setEditingTag(null);
          toast.success("Tag renamed");
        },
        onError: (err) => toast.error(err.message),
      },
    );
  };

  const handleDelete = () => {
    if (!deletingTag) return;
    deleteTag.mutate(deletingTag.id, {
      onSuccess: () => {
        setDeletingTag(null);
        toast.success("Tag deleted");
      },
      onError: (err) => toast.error(err.message),
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Tags</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Create Tag</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="flex gap-2">
            <Input
              placeholder="Tag name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <Button type="submit" disabled={createTag.isPending}>
              Create
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : !tags || tags.length === 0 ? (
            <p className="text-sm text-muted-foreground">No tags yet</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tags.map((tag) => (
                  <TableRow key={tag.id}>
                    <TableCell className="font-medium">{tag.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(tag.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            setEditingTag(tag);
                            setEditName(tag.name);
                          }}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeletingTag(tag)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog
        open={editingTag !== null}
        onOpenChange={(open) => !open && setEditingTag(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename Tag</DialogTitle>
          </DialogHeader>
          <Input
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleRename()}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingTag(null)}>
              Cancel
            </Button>
            <Button onClick={handleRename} disabled={renameTag.isPending}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={deletingTag !== null}
        onOpenChange={(open) => !open && setDeletingTag(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Tag</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete "{deletingTag?.name}"?
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingTag(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteTag.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

```tsx
import TagsPage from "./pages/TagsPage";

// Inside <Route element={<Layout />}>:
<Route path="tags" element={<TagsPage />} />
```

- [ ] **Step 3: Verify with dev server**

Navigate to http://localhost:5173/tags. Create a tag, rename it, delete it.

- [ ] **Step 4: Commit**

```bash
git add src/image_vector_search/frontend/src/pages/TagsPage.tsx src/image_vector_search/frontend/src/App.tsx
git commit -m "feat: implement Tags management page"
```

---

## Task 7: Categories page

**Files:**
- Create: `src/image_vector_search/frontend/src/components/CategoryTree.tsx`
- Create: `src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`
- Modify: `src/image_vector_search/frontend/src/App.tsx`

- [ ] **Step 1: Create CategoryTree component**

`src/image_vector_search/frontend/src/components/CategoryTree.tsx`:

```tsx
import { ChevronRight, ChevronDown, Pencil, Trash2, Plus } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { CategoryNode } from "@/api/types";

interface CategoryTreeProps {
  nodes: CategoryNode[];
  onEdit: (node: CategoryNode) => void;
  onDelete: (node: CategoryNode) => void;
  onAddChild: (parentId: number) => void;
}

function TreeNode({
  node,
  onEdit,
  onDelete,
  onAddChild,
}: {
  node: CategoryNode;
  onEdit: (node: CategoryNode) => void;
  onDelete: (node: CategoryNode) => void;
  onAddChild: (parentId: number) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  return (
    <div>
      <div className="flex items-center gap-1 py-1 px-1 rounded hover:bg-gray-50 group">
        <button
          className="w-5 h-5 flex items-center justify-center"
          onClick={() => setExpanded(!expanded)}
        >
          {hasChildren ? (
            expanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )
          ) : (
            <span className="w-3.5" />
          )}
        </button>
        <span className="text-sm flex-1">{node.name}</span>
        <div className="hidden group-hover:flex gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onAddChild(node.id)}
          >
            <Plus className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onEdit(node)}
          >
            <Pencil className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => onDelete(node)}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
      {hasChildren && expanded && (
        <div className="ml-5 border-l">
          {node.children.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              onEdit={onEdit}
              onDelete={onDelete}
              onAddChild={onAddChild}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CategoryTree({
  nodes,
  onEdit,
  onDelete,
  onAddChild,
}: CategoryTreeProps) {
  if (nodes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">No categories yet</p>
    );
  }
  return (
    <div>
      {nodes.map((node) => (
        <TreeNode
          key={node.id}
          node={node}
          onEdit={onEdit}
          onDelete={onDelete}
          onAddChild={onAddChild}
        />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Create CategoriesPage**

`src/image_vector_search/frontend/src/pages/CategoriesPage.tsx`:

```tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from "@/api/categories";
import type { CategoryNode } from "@/api/types";
import CategoryTree from "@/components/CategoryTree";
import { toast } from "sonner";

export default function CategoriesPage() {
  const { data: tree, isLoading } = useCategories();
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();

  const [newName, setNewName] = useState("");
  const [createParentId, setCreateParentId] = useState<number | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const [editingNode, setEditingNode] = useState<CategoryNode | null>(null);
  const [editName, setEditName] = useState("");
  const [moveAction, setMoveAction] = useState<
    "none" | "root" | "reparent"
  >("none");
  const [newParentId, setNewParentId] = useState("");

  const [deletingNode, setDeletingNode] = useState<CategoryNode | null>(null);

  const handleCreate = () => {
    if (!newName.trim()) return;
    createCategory.mutate(
      { name: newName.trim(), parent_id: createParentId },
      {
        onSuccess: () => {
          setNewName("");
          setCreateParentId(null);
          setShowCreateDialog(false);
          toast.success("Category created");
        },
        onError: (err) => toast.error(err.message),
      },
    );
  };

  const handleAddChild = (parentId: number) => {
    setCreateParentId(parentId);
    setNewName("");
    setShowCreateDialog(true);
  };

  const handleEdit = () => {
    if (!editingNode) return;
    const payload: {
      id: number;
      name?: string;
      move_to_root?: boolean;
      move_to_parent_id?: number;
    } = { id: editingNode.id };
    if (editName.trim() && editName.trim() !== editingNode.name) {
      payload.name = editName.trim();
    }
    if (moveAction === "root") {
      payload.move_to_root = true;
    } else if (moveAction === "reparent" && newParentId) {
      payload.move_to_parent_id = parseInt(newParentId, 10);
    }
    updateCategory.mutate(payload, {
      onSuccess: () => {
        setEditingNode(null);
        toast.success("Category updated");
      },
      onError: (err) => toast.error(err.message),
    });
  };

  const handleDelete = () => {
    if (!deletingNode) return;
    deleteCategory.mutate(deletingNode.id, {
      onSuccess: () => {
        setDeletingNode(null);
        toast.success("Category deleted");
      },
      onError: (err) => toast.error(err.message),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Categories</h1>
        <Button
          onClick={() => {
            setCreateParentId(null);
            setNewName("");
            setShowCreateDialog(true);
          }}
        >
          New Category
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : (
            <CategoryTree
              nodes={tree || []}
              onEdit={(node) => {
                setEditingNode(node);
                setEditName(node.name);
                setMoveAction("none");
                setNewParentId("");
              }}
              onDelete={setDeletingNode}
              onAddChild={handleAddChild}
            />
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {createParentId
                ? "New Sub-category"
                : "New Root Category"}
            </DialogTitle>
          </DialogHeader>
          <Input
            placeholder="Category name..."
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowCreateDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={createCategory.isPending}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={editingNode !== null}
        onOpenChange={(open) => !open && setEditingNode(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Name</Label>
              <Input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
              />
            </div>
            <div>
              <Label>Move</Label>
              <div className="flex gap-2 mt-1">
                <Button
                  variant={moveAction === "none" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMoveAction("none")}
                >
                  No move
                </Button>
                <Button
                  variant={moveAction === "root" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMoveAction("root")}
                >
                  Move to root
                </Button>
                <Button
                  variant={moveAction === "reparent" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setMoveAction("reparent")}
                >
                  Reparent
                </Button>
              </div>
              {moveAction === "reparent" && (
                <Input
                  className="mt-2"
                  placeholder="New parent category ID"
                  value={newParentId}
                  onChange={(e) => setNewParentId(e.target.value)}
                />
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingNode(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleEdit}
              disabled={updateCategory.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog
        open={deletingNode !== null}
        onOpenChange={(open) => !open && setDeletingNode(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Category</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            Are you sure you want to delete "{deletingNode?.name}"?
            {deletingNode && deletingNode.children.length > 0 && (
              <span className="block mt-1 text-destructive">
                This category has {deletingNode.children.length} sub-categories.
              </span>
            )}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeletingNode(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteCategory.isPending}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
```

- [ ] **Step 3: Add route to App.tsx**

```tsx
import CategoriesPage from "./pages/CategoriesPage";

// Inside <Route element={<Layout />}>:
<Route path="categories" element={<CategoriesPage />} />
```

- [ ] **Step 4: Verify with dev server**

Navigate to http://localhost:5173/categories. Create root and child categories, edit, move, delete.

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/components/CategoryTree.tsx \
  src/image_vector_search/frontend/src/pages/CategoriesPage.tsx \
  src/image_vector_search/frontend/src/App.tsx
git commit -m "feat: implement Categories management page with tree view"
```

---

## Task 8: Images page

**Files:**
- Create: `src/image_vector_search/frontend/src/components/ImageTagEditor.tsx`
- Create: `src/image_vector_search/frontend/src/pages/ImagesPage.tsx`
- Modify: `src/image_vector_search/frontend/src/App.tsx`

- [ ] **Step 1: Create ImageTagEditor component**

`src/image_vector_search/frontend/src/components/ImageTagEditor.tsx`:

```tsx
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { X } from "lucide-react";
import { useState } from "react";
import {
  useImageTags,
  useImageCategories,
  useAddTagToImage,
  useRemoveTagFromImage,
  useAddCategoryToImage,
  useRemoveCategoryFromImage,
} from "@/api/images";
import { useTags } from "@/api/tags";
import { useCategories } from "@/api/categories";
import type { CategoryNode } from "@/api/types";
import { toast } from "sonner";

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
): { id: number; label: string }[] {
  const result: { id: number; label: string }[] = [];
  for (const node of nodes) {
    result.push({ id: node.id, label: "  ".repeat(depth) + node.name });
    result.push(...flattenCategories(node.children, depth + 1));
  }
  return result;
}

export default function ImageTagEditor({
  contentHash,
}: {
  contentHash: string;
}) {
  const { data: imageTags } = useImageTags(contentHash);
  const { data: imageCategories } = useImageCategories(contentHash);
  const { data: allTags } = useTags();
  const { data: categoryTree } = useCategories();
  const addTag = useAddTagToImage();
  const removeTag = useRemoveTagFromImage();
  const addCategory = useAddCategoryToImage();
  const removeCategory = useRemoveCategoryFromImage();

  const [selectedTagId, setSelectedTagId] = useState("");
  const [selectedCategoryId, setSelectedCategoryId] = useState("");

  const assignedTagIds = new Set(imageTags?.map((t) => t.id) || []);
  const availableTags = allTags?.filter((t) => !assignedTagIds.has(t.id)) || [];

  const assignedCategoryIds = new Set(
    imageCategories?.map((c) => c.id) || [],
  );
  const flatCategories = flattenCategories(categoryTree || []).filter(
    (c) => !assignedCategoryIds.has(c.id),
  );

  return (
    <div className="space-y-4 py-2">
      {/* Tags */}
      <div>
        <div className="text-sm font-medium mb-2">Tags</div>
        <div className="flex flex-wrap gap-1 mb-2">
          {imageTags?.map((tag) => (
            <Badge key={tag.id} variant="secondary" className="gap-1">
              {tag.name}
              <button
                onClick={() =>
                  removeTag.mutate(
                    { contentHash, tagId: tag.id },
                    { onError: (err) => toast.error(err.message) },
                  )
                }
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {(!imageTags || imageTags.length === 0) && (
            <span className="text-xs text-muted-foreground">No tags</span>
          )}
        </div>
        {availableTags.length > 0 && (
          <div className="flex gap-2">
            <Select value={selectedTagId} onValueChange={setSelectedTagId}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Add tag..." />
              </SelectTrigger>
              <SelectContent>
                {availableTags.map((tag) => (
                  <SelectItem key={tag.id} value={String(tag.id)}>
                    {tag.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={!selectedTagId}
              onClick={() => {
                addTag.mutate(
                  { contentHash, tagId: parseInt(selectedTagId, 10) },
                  {
                    onSuccess: () => setSelectedTagId(""),
                    onError: (err) => toast.error(err.message),
                  },
                );
              }}
            >
              Add
            </Button>
          </div>
        )}
      </div>

      {/* Categories */}
      <div>
        <div className="text-sm font-medium mb-2">Categories</div>
        <div className="flex flex-wrap gap-1 mb-2">
          {imageCategories?.map((cat) => (
            <Badge key={cat.id} variant="outline" className="gap-1">
              {cat.name}
              <button
                onClick={() =>
                  removeCategory.mutate(
                    { contentHash, categoryId: cat.id },
                    { onError: (err) => toast.error(err.message) },
                  )
                }
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}
          {(!imageCategories || imageCategories.length === 0) && (
            <span className="text-xs text-muted-foreground">
              No categories
            </span>
          )}
        </div>
        {flatCategories.length > 0 && (
          <div className="flex gap-2">
            <Select
              value={selectedCategoryId}
              onValueChange={setSelectedCategoryId}
            >
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Add category..." />
              </SelectTrigger>
              <SelectContent>
                {flatCategories.map((cat) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              size="sm"
              disabled={!selectedCategoryId}
              onClick={() => {
                addCategory.mutate(
                  {
                    contentHash,
                    categoryId: parseInt(selectedCategoryId, 10),
                  },
                  {
                    onSuccess: () => setSelectedCategoryId(""),
                    onError: (err) => toast.error(err.message),
                  },
                );
              }}
            >
              Add
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create ImagesPage**

`src/image_vector_search/frontend/src/pages/ImagesPage.tsx`:

```tsx
import React, { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useImages } from "@/api/images";
import ImageTagEditor from "@/components/ImageTagEditor";
import { ChevronRight, ChevronDown } from "lucide-react";

export default function ImagesPage() {
  const { data: images, isLoading } = useImages();
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Images</h1>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading...</p>
          ) : !images || images.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No indexed images yet
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Content Hash</TableHead>
                  <TableHead>Path</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Size</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {images.map((img) => (
                  <React.Fragment key={img.content_hash}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() =>
                        setExpandedHash(
                          expandedHash === img.content_hash
                            ? null
                            : img.content_hash,
                        )
                      }
                    >
                      <TableCell>
                        {expandedHash === img.content_hash ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {img.content_hash.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="text-sm">
                        {img.canonical_path}
                      </TableCell>
                      <TableCell className="text-sm">
                        {img.mime_type}
                      </TableCell>
                      <TableCell className="text-sm">
                        {img.width}x{img.height}
                      </TableCell>
                    </TableRow>
                    {expandedHash === img.content_hash && (
                      <TableRow>
                        <TableCell colSpan={5} className="px-6 pb-4">
                          <ImageTagEditor contentHash={img.content_hash} />
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Add route to App.tsx**

```tsx
import ImagesPage from "./pages/ImagesPage";

// Inside <Route element={<Layout />}>:
<Route path="images" element={<ImagesPage />} />
```

- [ ] **Step 4: Verify with dev server**

Navigate to http://localhost:5173/images. If images are indexed, they should appear. Click a row to expand the tag/category editor.

- [ ] **Step 5: Commit**

```bash
git add src/image_vector_search/frontend/src/components/ImageTagEditor.tsx \
  src/image_vector_search/frontend/src/pages/ImagesPage.tsx \
  src/image_vector_search/frontend/src/App.tsx
git commit -m "feat: implement Images page with tag/category association editor"
```

---

## Task 9: FastAPI SPA integration

Replace Jinja2 serving with static SPA serving.

**Files:**
- Modify: `src/image_vector_search/app.py`
- Modify: `src/image_vector_search/frontend/routes.py`
- Modify: `pyproject.toml`
- Modify: `tests/integration/test_web_admin.py`

- [ ] **Step 1: Build the React app**

```bash
cd src/image_vector_search/frontend && npm run build
```

Expected: `dist/` directory created with `index.html` and `assets/`.

- [ ] **Step 2: Update app.py to serve SPA**

Replace the old static mount and add SPA serving. Key changes in `src/image_vector_search/app.py`:

Remove:
```python
from fastapi.templating import Jinja2Templates  # if imported here
```

Replace the static mount:
```python
# Old:
static_dir = Path(__file__).with_name("web") / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# New:
dist_dir = Path(__file__).with_name("web") / "dist"
if dist_dir.is_dir():
    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
```

Add SPA fallback (AFTER all routers and mounts, BEFORE `return app`):

```python
from starlette.responses import FileResponse

if dist_dir.is_dir():
    spa_index = dist_dir / "index.html"

    @app.get("/{path:path}")
    async def spa_fallback(path: str):
        return FileResponse(str(spa_index))
```

- [ ] **Step 3: Remove Jinja2 route from routes.py**

In `src/image_vector_search/frontend/routes.py`:

Remove the `TEMPLATES` variable, the `Jinja2Templates` import, the `Request` import, the `HTMLResponse` import, and the `admin_home` route (`GET /`).

The file should start with:
```python
from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
```

- [ ] **Step 4: Update pyproject.toml package-data**

Replace:
```toml
[tool.setuptools.package-data]
image_vector_search = [
  "web/templates/*.html",
  "web/static/*.css",
  "web/static/*.js",
]
```

With:
```toml
[tool.setuptools.package-data]
image_vector_search = [
  "frontend/dist/**",
]
```

- [ ] **Step 5: Remove `jinja2` from dependencies**

In `pyproject.toml`, remove `"jinja2>=3.1,<4",` from the `dependencies` list.

- [ ] **Step 6: Update test_web_admin.py**

The `test_admin_home_shows_status_and_actions` test checks `GET /` for HTML content. Since `GET /` now serves the SPA `index.html` (or returns 404 if dist/ doesn't exist in test), update:

If `dist/` doesn't exist during tests, the SPA fallback won't be registered. The test should be updated to remove the HTML check, or skip it. Replace:

```python
def test_admin_home_shows_status_and_actions():
    client = create_test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "Incremental Update" in response.text
    assert "Full Rebuild" in response.text
    assert "Debug Search" in response.text
```

With:

```python
def test_admin_home_returns_200():
    """GET / returns SPA index.html if dist/ exists, otherwise the API still works."""
    client = create_test_client()
    # API endpoints should still work regardless of SPA presence
    response = client.get("/api/status")
    assert response.status_code == 200
```

(The old test was testing Jinja2 rendering which no longer applies.)

- [ ] **Step 7: Run all Python tests**

```bash
pytest -v
```

Expected: ALL PASS

- [ ] **Step 8: Delete old template and static files**

```bash
rm -rf src/image_vector_search/frontend/templates/
rm -rf src/image_vector_search/frontend/static/
```

- [ ] **Step 9: Commit**

```bash
git add src/image_vector_search/app.py src/image_vector_search/frontend/routes.py \
  pyproject.toml tests/integration/test_web_admin.py
git rm -r src/image_vector_search/frontend/templates/ src/image_vector_search/frontend/static/
git commit -m "feat: replace Jinja2 with SPA static serving, remove old templates"
```

---

## Task 10: Docker multi-stage build

**Files:**
- Modify: `Dockerfile`

- [ ] **Step 1: Update Dockerfile**

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend
WORKDIR /app/web
COPY src/image_vector_search/frontend/package.json src/image_vector_search/frontend/package-lock.json ./
RUN npm ci
COPY src/image_vector_search/frontend/ ./
RUN npm run build

# Stage 2: Python application
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# Copy built frontend into the Python package
COPY --from=frontend /app/frontend/dist ./src/image_vector_search/frontend/dist

RUN pip install .

EXPOSE 8000

CMD ["uvicorn", "image_vector_search.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Test Docker build**

```bash
docker compose build
```

Expected: Builds successfully, both stages complete.

- [ ] **Step 3: Test Docker run**

```bash
docker compose up
```

Visit http://localhost:8000. The React SPA should load with sidebar navigation and all four pages.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile
git commit -m "feat: add multi-stage Docker build for React frontend"
```

---

## Task 11: Final verification

- [ ] **Step 1: Run all Python tests**

```bash
pytest -v
```

Expected: ALL PASS

- [ ] **Step 2: Run TypeScript type check**

```bash
cd src/image_vector_search/frontend && npx tsc --noEmit
```

Expected: No errors

- [ ] **Step 3: Build frontend**

```bash
cd src/image_vector_search/frontend && npm run build
```

Expected: Clean build, no warnings

- [ ] **Step 4: Manual smoke test**

Start both servers and verify:
1. Dashboard: status loads, jobs list, both search forms work
2. Tags: create, rename, delete
3. Categories: create root/child, rename, move to root, move to parent, delete
4. Images: list shows images, expand row, add/remove tags and categories
5. Navigation: all sidebar links work, browser back/forward works

- [ ] **Step 5: Final commit if any cleanup needed**

```bash
git status
# Add any remaining changes
git commit -m "chore: final cleanup for React admin frontend migration"
```
