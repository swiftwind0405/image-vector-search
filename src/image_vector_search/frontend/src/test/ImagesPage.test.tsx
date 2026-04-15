import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
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
    useAddTagToImage: () => ({ mutate: vi.fn() }),
    useRemoveTagFromImage: () => ({ mutate: vi.fn() }),
  };
});

vi.mock("../api/tags", () => ({
  useTags: () => ({ data: [] }),
  useCreateTag: () => ({ isPending: false, mutate: vi.fn() }),
}));

import ImagesPage from "../pages/ImagesPage";

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
    indexed: true,
    indexed_content_hash: contentHash,
    file_url: `/api/images/${contentHash}/file`,
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, refetchOnWindowFocus: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ImagesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImagesPage", () => {
  const fetchMock = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders all filesystem images and indexed state badges", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            makeImage("img-1", "/data/images/a.jpg"),
            makeImage("fs:/data/images/b.jpg", "/data/images/b.jpg", {
              indexed: false,
              indexed_content_hash: null,
              file_url: "/api/folders/file?path=%2Fdata%2Fimages%2Fb.jpg",
            }),
          ],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPage();

    expect(await screen.findByAltText("a.jpg")).toBeInTheDocument();
    expect(screen.getByAltText("b.jpg")).toBeInTheDocument();
    expect(screen.getByText("Indexed")).toBeInTheDocument();
    expect(screen.getByText("Unindexed")).toBeInTheDocument();
  });

  it("opens image modal for unindexed files", async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            makeImage("fs:/data/images/b.jpg", "/data/images/b.jpg", {
              indexed: false,
              indexed_content_hash: null,
              file_url: "/api/folders/file?path=%2Fdata%2Fimages%2Fb.jpg",
            }),
          ],
          next_cursor: null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    renderPage();
    const user = userEvent.setup();

    await user.click(await screen.findByAltText("b.jpg"));

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Not indexed yet")).toBeInTheDocument();
  });
});
