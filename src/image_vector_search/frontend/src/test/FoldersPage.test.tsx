import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../api/bulk", () => ({
  useOpenFile: () => ({ mutate: vi.fn() }),
  useRevealFile: () => ({ mutate: vi.fn() }),
}));

vi.mock("../api/images", async () => {
  const actual = await vi.importActual<typeof import("../api/images")>("../api/images");
  return {
    ...actual,
    useImageTags: () => ({ data: [] }),
    useImageCategories: () => ({ data: [] }),
    useAddTagToImage: () => ({ mutate: vi.fn() }),
    useRemoveTagFromImage: () => ({ mutate: vi.fn() }),
    useAddCategoryToImage: () => ({ mutate: vi.fn() }),
    useRemoveCategoryFromImage: () => ({ mutate: vi.fn() }),
  };
});

vi.mock("../api/tags", () => ({
  useTags: () => ({ data: [] }),
  useCreateTag: () => ({ isPending: false, mutate: vi.fn() }),
}));

vi.mock("../api/categories", () => ({
  useCategories: () => ({ data: [] }),
  useCreateCategory: () => ({ isPending: false, mutate: vi.fn() }),
}));

import FoldersPage from "../pages/FoldersPage";

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}{location.search}</div>;
}

function makeImage(
  contentHash: string,
  canonicalPath: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    content_hash: contentHash,
    canonical_path: canonicalPath,
    file_size: 1000,
    mtime: 1000,
    mime_type: "image/jpeg",
    width: 100,
    height: 100,
    is_active: true,
    last_seen_at: "2026-04-11T00:00:00Z",
    embedding_provider: "jina",
    embedding_model: "jina-clip-v2",
    embedding_version: "v2",
    embedding_status: "embedded" as const,
    created_at: "2026-04-11T00:00:00Z",
    updated_at: "2026-04-11T00:00:00Z",
    tags: [],
    categories: [],
    indexed: true,
    indexed_content_hash: contentHash,
    file_url: `/api/images/${contentHash}/file`,
    ...overrides,
  };
}

function renderPage(initialEntry = "/folders") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route
            path="/folders"
            element={
              <>
                <LocationProbe />
                <FoldersPage />
              </>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FoldersPage", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders root folders and direct images", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          path: "",
          parent: null,
          folders: ["a", "b"],
          images: [makeImage("img-1", "/data/images/root/img1.jpg")],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPage("/folders");

    expect(await screen.findByRole("link", { name: "a" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "b" })).toBeInTheDocument();
    expect(screen.getByAltText("img1.jpg")).toBeInTheDocument();
    expect(screen.getByText("Indexed")).toBeInTheDocument();
  });

  it("clicking a subfolder drills down", async () => {
    const requests: string[] = [];
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      const path = new URL(url, "http://test").searchParams.get("path") ?? "";
      return new Response(
        JSON.stringify({
          path,
          parent: path ? null : null,
          folders: path === "" ? ["a"] : [],
          images: [],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    renderPage("/folders");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: "a" }));

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/folders?path=a");
    });
    expect(requests).toContain("/api/folders/browse");
    expect(requests).toContain("/api/folders/browse?path=a");
  });

  it("breadcrumb navigation jumps back up the tree", async () => {
    fetchMock.mockImplementation(async (input) => {
      const path = new URL(String(input), "http://test").searchParams.get("path") ?? "";
      return new Response(
        JSON.stringify({
          path,
          parent: "a/b",
          folders: [],
          images: [],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    renderPage("/folders?path=a/b/c");
    const user = userEvent.setup();

    expect(await screen.findByText("Root")).toBeInTheDocument();
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
    expect(screen.getByText("c")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "a" }));

    await waitFor(() => {
      expect(screen.getByTestId("location")).toHaveTextContent("/folders?path=a");
    });
  });

  it("image click opens the shared image modal", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          path: "a",
          parent: "",
          folders: [],
          images: [
            makeImage("fs:/data/images/a/detail.jpg", "/data/images/a/detail.jpg", {
              indexed: false,
              indexed_content_hash: null,
              file_url: "/api/folders/file?path=%2Fdata%2Fimages%2Fa%2Fdetail.jpg",
            }),
          ],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPage("/folders?path=a");
    const user = userEvent.setup();

    await user.click(await screen.findByAltText("detail.jpg"));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Not indexed yet")).toBeInTheDocument();
  });

  it("shows an empty state for empty folders", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          path: "a",
          parent: "",
          folders: [],
          images: [],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPage("/folders?path=a");

    expect(await screen.findByText("This folder is empty.")).toBeInTheDocument();
  });

  it("loads a deep link with the requested path", async () => {
    const requests: string[] = [];
    fetchMock.mockImplementation(async (input) => {
      const url = String(input);
      requests.push(url);
      return new Response(
        JSON.stringify({
          path: "a/b/c",
          parent: "a/b",
          folders: ["a/b/c/d"],
          images: [makeImage("img-deep", "/data/images/a/b/c/deep.jpg")],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    renderPage("/folders?path=a/b/c");

    expect(await screen.findByText("d")).toBeInTheDocument();
    expect(screen.getByAltText("deep.jpg")).toBeInTheDocument();
    expect(requests).toContain("/api/folders/browse?path=a%2Fb%2Fc");
  });
});
