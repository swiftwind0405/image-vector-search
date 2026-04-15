import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FilterBar from "../components/FilterBar";
import type { Tag } from "../api/types";

const makeTag = (id: number, name: string): Tag => ({
  id,
  name,
  created_at: "2026-01-01T00:00:00",
  image_count: null,
});

describe("FilterBar", () => {
  const tags = [makeTag(1, "nature"), makeTag(2, "travel")];

  it("renders tag chips", () => {
    render(
      <FilterBar
        tags={tags}
        activeTags={[]}
        onTagToggle={vi.fn()}
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
        activeTags={[]}
        onTagToggle={onTagToggle}
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
        activeTags={["nature"]}
        onTagToggle={onTagToggle}
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
        activeTags={["nature"]}
        onTagToggle={vi.fn()}
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
        activeTags={[]}
        onTagToggle={vi.fn()}
        onClear={vi.fn()}
      />,
    );
    expect(screen.queryByText("Clear all")).not.toBeInTheDocument();
  });
});
