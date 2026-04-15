import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import Layout from "../components/Layout";
import TagsPage from "../pages/TagsPage";
import DashboardPage from "../pages/DashboardPage";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../api/auth", () => ({
  useLogout: () => ({ mutateAsync: vi.fn() }),
}));

vi.mock("../api/status", () => ({
  useStatus: () => ({
    data: {
      images_on_disk: 240,
      active_images: 180,
      inactive_images: 12,
      vector_entries: 180,
      embedding_provider: "jina",
      embedding_model: "jina-clip-v2",
      embedding_version: "2026-04",
    },
    isFetching: false,
  }),
}));

const inactiveImages = [
  {
    content_hash: "inactive-1",
    canonical_path: "/data/images/old-1.jpg",
    file_size: 120,
    mtime: 1000,
    mime_type: "image/jpeg",
    width: 12,
    height: 8,
    is_active: false,
    last_seen_at: "2026-04-07T00:00:00Z",
    embedding_provider: "jina",
    embedding_model: "jina-clip-v2",
    embedding_version: "2026-04",
    created_at: "2026-04-07T00:00:00Z",
    updated_at: "2026-04-07T00:00:00Z",
  },
  {
    content_hash: "inactive-2",
    canonical_path: "/data/images/old-2.jpg",
    file_size: 140,
    mtime: 1001,
    mime_type: "image/jpeg",
    width: 16,
    height: 9,
    is_active: false,
    last_seen_at: "2026-04-07T00:00:00Z",
    embedding_provider: "jina",
    embedding_model: "jina-clip-v2",
    embedding_version: "2026-04",
    created_at: "2026-04-07T00:00:00Z",
    updated_at: "2026-04-07T00:00:00Z",
  },
];

const purgeInactiveMutate = vi.fn();
const queueJobMutate = vi.fn();

vi.mock("../api/images", () => ({
  useInactiveImages: () => ({
    data: inactiveImages,
    isLoading: false,
  }),
  useImages: () => ({
    data: [],
    isLoading: false,
  }),
  useImagesInfinite: () => ({
    data: { pages: [] },
    isLoading: false,
    hasNextPage: false,
    isFetchingNextPage: false,
    fetchNextPage: vi.fn(),
  }),
  useForceEmbedImages: () => ({
    isPending: false,
    mutate: vi.fn(),
  }),
  usePurgeInactiveImages: () => ({
    isPending: false,
    mutate: purgeInactiveMutate,
  }),
}));

vi.mock("../api/jobs", () => ({
  useJobs: () => ({
    data: [{ id: 1, job_type: "incremental", status: "queued" }],
    isFetching: false,
  }),
  useQueueJob: () => ({ isPending: false, mutate: queueJobMutate }),
}));

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>("@tanstack/react-query");
  return {
    ...actual,
    useQueryClient: () => ({
      invalidateQueries: vi.fn(),
    }),
  };
});

vi.mock("../api/tags", () => ({
  useTags: () => ({
    data: [{ id: 3, name: "sunset", created_at: "2026-01-01T00:00:00", image_count: 1 }],
    isLoading: false,
  }),
  useCreateTag: () => ({ isPending: false, mutate: vi.fn() }),
  useRenameTag: () => ({ isPending: false, mutate: vi.fn() }),
  useDeleteTag: () => ({ isPending: false, mutate: vi.fn() }),
  useBulkDeleteTags: () => ({ isPending: false, mutate: vi.fn() }),
  useImportTags: () => ({ isPending: false, mutate: vi.fn() }),
}));

describe("admin shell redesign constraints", () => {
  it("renders the brand, route navigation, and a page context bar", () => {
    render(
      <MemoryRouter initialEntries={["/search"]}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/search" element={<div>Search workspace body</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getAllByText("Image Search").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("img", { name: "Image Search logo" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Dashboard" })[0]).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: "Search" })[0]).toHaveAttribute("href", "/search");
    expect(screen.getAllByRole("link", { name: "Tags" })[0]).toHaveAttribute("href", "/tags");
    expect(screen.getAllByRole("link", { name: "Images" })[0]).toHaveAttribute("href", "/images");
    expect(screen.getByRole("heading", { name: "Search Workspace", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Search workspace body")).toBeInTheDocument();
  });

  it("renders a dashboard overview with primary actions and recent activity", () => {
    render(<DashboardPage />);

    expect(screen.getByText("Collection Overview")).toBeInTheDocument();
    expect(screen.getByText("Incremental Update")).toBeInTheDocument();
    expect(screen.getByText("Full Rebuild")).toBeInTheDocument();
    expect(screen.getByText("Recent Activity")).toBeInTheDocument();
    expect(screen.getByText("jina")).toBeInTheDocument();
  });

  it("requires confirmation before queueing indexing jobs", async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: "Incremental Update" }));
    expect(screen.getByRole("heading", { name: "Confirm Incremental Update", level: 2 })).toBeInTheDocument();
    expect(queueJobMutate).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Confirm" }));
    await waitFor(() => {
      expect(queueJobMutate).toHaveBeenCalledWith("incremental", expect.any(Object));
    });

    queueJobMutate.mockClear();

    await user.click(screen.getByRole("button", { name: "Full Rebuild" }));
    expect(screen.getByRole("heading", { name: "Confirm Full Rebuild", level: 2 })).toBeInTheDocument();
    expect(queueJobMutate).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(queueJobMutate).not.toHaveBeenCalled();
  });

  it("defaults inactive purge dialog to all selected and submits chosen hashes", async () => {
    const user = userEvent.setup();
    render(<DashboardPage />);

    await user.click(screen.getByRole("button", { name: "Purge Inactive" }));
    expect(screen.getByRole("heading", { name: "Purge Inactive", level: 2 })).toBeInTheDocument();
    expect(screen.getByText("2 selected")).toBeInTheDocument();

    await user.click(screen.getByText("/data/images/old-2.jpg"));
    await user.click(screen.getByRole("button", { name: "Purge 1 Image" }));

    await waitFor(() => {
      expect(purgeInactiveMutate).toHaveBeenCalledWith(
        { content_hashes: ["inactive-1"] },
        expect.any(Object),
      );
    });
  });

  it("renders a tag image detail link from the tags page", () => {
    render(
      <MemoryRouter>
        <TagsPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "sunset" })).toHaveAttribute(
      "href",
      "/tags/3/images",
    );
  });
});
