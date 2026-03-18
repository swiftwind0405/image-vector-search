import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import TagsPage from "../pages/TagsPage";
import CategoriesPage from "../pages/CategoriesPage";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("../api/tags", () => ({
  useTags: () => ({
    data: [{ id: 3, name: "sunset", created_at: "2026-01-01T00:00:00", image_count: 1 }],
    isLoading: false,
  }),
  useCreateTag: () => ({ isPending: false, mutate: vi.fn() }),
  useRenameTag: () => ({ isPending: false, mutate: vi.fn() }),
  useDeleteTag: () => ({ isPending: false, mutate: vi.fn() }),
  useBulkDeleteTags: () => ({ isPending: false, mutate: vi.fn() }),
}));

vi.mock("../api/categories", () => ({
  useCategories: () => ({
    data: [
      {
        id: 10,
        name: "Nature",
        parent_id: null,
        sort_order: 0,
        created_at: "2026-01-01T00:00:00",
        children: [],
        image_count: 1,
      },
    ],
    isLoading: false,
  }),
  useCreateCategory: () => ({ isPending: false, mutate: vi.fn() }),
  useUpdateCategory: () => ({ isPending: false, mutate: vi.fn() }),
  useDeleteCategory: () => ({ isPending: false, mutate: vi.fn() }),
  useBulkDeleteCategories: () => ({ isPending: false, mutate: vi.fn() }),
}));

describe("admin navigation into image detail pages", () => {
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

  it("renders a category image detail link from the categories page", () => {
    render(
      <MemoryRouter>
        <CategoriesPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Nature (1)" })).toHaveAttribute(
      "href",
      "/categories/10/images",
    );
  });
});
