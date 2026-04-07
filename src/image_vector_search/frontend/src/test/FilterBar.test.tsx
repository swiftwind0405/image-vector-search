import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilterBar from "../components/FilterBar";
import type { Tag, CategoryNode } from "../api/types";

const makeTag = (id: number, name: string): Tag => ({
  id,
  name,
  created_at: "2026-01-01T00:00:00",
  image_count: null,
});

const makeCategoryNode = (id: number, name: string): CategoryNode => ({
  id,
  name,
  parent_id: null,
  sort_order: 0,
  created_at: "2026-01-01T00:00:00",
  children: [],
  image_count: null,
});

describe("FilterBar", () => {
  const tags = [makeTag(1, "nature"), makeTag(2, "travel")];
  const categories = [makeCategoryNode(10, "Travel"), makeCategoryNode(20, "Work")];

  it("renders tag chips", () => {
    render(
      <FilterBar
        tags={tags}
        categories={[]}
        activeTags={[]}
        activeCategoryId={null}
        onTagToggle={vi.fn()}
        onCategoryToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    expect(screen.getByText("nature")).toBeInTheDocument();
    expect(screen.getByText("travel")).toBeInTheDocument();
  });

  it("calls onTagToggle with tag name when inactive tag is clicked", async () => {
    const onTagToggle = vi.fn();
    render(
      <FilterBar
        tags={tags}
        categories={[]}
        activeTags={[]}
        activeCategoryId={null}
        onTagToggle={onTagToggle}
        onCategoryToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByText("nature"));
    expect(onTagToggle).toHaveBeenCalledWith("nature");
  });

  it("calls onTagToggle again when active tag is clicked (toggle off)", async () => {
    const onTagToggle = vi.fn();
    render(
      <FilterBar
        tags={tags}
        categories={[]}
        activeTags={["nature"]}
        activeCategoryId={null}
        onTagToggle={onTagToggle}
        onCategoryToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    // Active tag button contains the X icon and the name; click the button
    const buttons = screen.getAllByRole("button");
    const natureBtn = buttons.find((b) => b.textContent?.includes("nature"));
    await userEvent.click(natureBtn!);
    expect(onTagToggle).toHaveBeenCalledWith("nature");
  });

  it("shows 'Clear all' when filters are active and calls onClear", async () => {
    const onClear = vi.fn();
    render(
      <FilterBar
        tags={tags}
        categories={categories}
        activeTags={["nature"]}
        activeCategoryId={null}
        onTagToggle={vi.fn()}
        onCategoryToggle={vi.fn()}
        onClear={onClear}
      />,
    );
    const clearBtn = screen.getByText("Clear all");
    expect(clearBtn).toBeInTheDocument();
    await userEvent.click(clearBtn);
    expect(onClear).toHaveBeenCalled();
  });

  it("does not show 'Clear all' when no filters are active", () => {
    render(
      <FilterBar
        tags={tags}
        categories={categories}
        activeTags={[]}
        activeCategoryId={null}
        onTagToggle={vi.fn()}
        onCategoryToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    expect(screen.queryByText("Clear all")).not.toBeInTheDocument();
  });
});
