import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import ImageModal from "../components/ImageModal";
import type { ImageRecordWithLabels } from "../api/types";

const addImagesMutateAsync = vi.fn();

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

vi.mock("../api/albums", () => ({
  useListAlbums: () => ({
    data: [
      {
        id: 1,
        name: "Favorites",
        type: "manual",
        description: "",
        rule_logic: null,
        source_paths: [],
        image_count: 2,
        cover_image: null,
        created_at: "2026-04-11T00:00:00Z",
        updated_at: "2026-04-11T00:00:00Z",
      },
      {
        id: 2,
        name: "Auto skies",
        type: "smart",
        description: "",
        rule_logic: "or",
        source_paths: [],
        image_count: 3,
        cover_image: null,
        created_at: "2026-04-11T00:00:00Z",
        updated_at: "2026-04-11T00:00:00Z",
      },
      {
        id: 3,
        name: "Print queue",
        type: "manual",
        description: "",
        rule_logic: null,
        source_paths: [],
        image_count: 0,
        cover_image: null,
        created_at: "2026-04-11T00:00:00Z",
        updated_at: "2026-04-11T00:00:00Z",
      },
    ],
  }),
  useAddImagesToAlbum: () => ({
    isPending: false,
    mutateAsync: addImagesMutateAsync,
  }),
}));

function makeImage(contentHash: string): ImageRecordWithLabels {
  return {
    content_hash: contentHash,
    canonical_path: `/data/images/${contentHash}.jpg`,
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
    embedding_status: "embedded",
    created_at: "2026-04-11T00:00:00Z",
    updated_at: "2026-04-11T00:00:00Z",
    indexed: true,
    indexed_content_hash: contentHash,
    file_url: `/api/images/${contentHash}/file`,
    tags: [],
  };
}

describe("ImageModal", () => {
  beforeAll(() => {
    if (!globalThis.PointerEvent) {
      globalThis.PointerEvent = MouseEvent as typeof PointerEvent;
    }
  });

  beforeEach(() => {
    addImagesMutateAsync.mockClear();
  });

  it("adds the current image to selected manual albums from the top bar", async () => {
    addImagesMutateAsync.mockResolvedValue({ added: 1 });
    const user = userEvent.setup();
    const image = makeImage("img-1");

    render(
      <ImageModal
        image={image}
        images={[image]}
        open
        onClose={vi.fn()}
        onNavigate={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Add to albums" }));

    expect(screen.getByText("Favorites")).toBeInTheDocument();
    expect(screen.getByText("Print queue")).toBeInTheDocument();
    expect(screen.queryByText("Auto skies")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Favorites"));
    await user.click(screen.getByLabelText("Print queue"));
    await user.click(screen.getByRole("button", { name: "Add to 2 albums" }));

    await waitFor(() => {
      expect(addImagesMutateAsync).toHaveBeenCalledWith({
        albumId: 1,
        contentHashes: ["img-1"],
      });
      expect(addImagesMutateAsync).toHaveBeenCalledWith({
        albumId: 3,
        contentHashes: ["img-1"],
      });
    });
  });
});
