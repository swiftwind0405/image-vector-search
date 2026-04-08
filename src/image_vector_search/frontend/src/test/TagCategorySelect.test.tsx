import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import TagSelect from "../components/TagSelect";
import CategorySelect from "../components/CategorySelect";
import type { CategoryNode, Tag } from "../api/types";

const makeTag = (id: number, name: string): Tag => ({
  id,
  name,
  created_at: "2026-01-01T00:00:00",
  image_count: null,
});

const makeCategory = (
  id: number,
  name: string,
  children: CategoryNode[] = [],
): CategoryNode => ({
  id,
  name,
  parent_id: null,
  sort_order: 0,
  created_at: "2026-01-01T00:00:00",
  children,
  image_count: null,
});

describe("TagSelect", () => {
  it("shows the selected tag text instead of the raw value", () => {
    render(
      <TagSelect
        tags={[makeTag(1, "Landscape"), makeTag(2, "Portrait")]}
        value="1"
        onValueChange={vi.fn()}
        onCreate={vi.fn()}
      />,
    );

    expect(screen.getByText("Landscape")).toBeInTheDocument();
    expect(screen.queryByText(/^1$/)).not.toBeInTheDocument();
  });

  it("supports creating a new tag directly", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(undefined);

    render(
      <TagSelect
        tags={[makeTag(1, "Landscape")]}
        value=""
        onValueChange={vi.fn()}
        onCreate={onCreate}
      />,
    );

    await user.click(screen.getByRole("button", { name: "New tag" }));
    await user.type(screen.getByLabelText("Tag name"), "Night");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(onCreate).toHaveBeenCalledWith("Night");
  });

  it("selects the created tag by default after creation", async () => {
    const user = userEvent.setup();
    const onValueChange = vi.fn();
    const onCreate = vi.fn().mockResolvedValue("3");

    render(
      <TagSelect
        tags={[makeTag(1, "Landscape")]}
        value=""
        onValueChange={onValueChange}
        onCreate={onCreate}
      />,
    );

    await user.click(screen.getByRole("button", { name: "New tag" }));
    await user.type(screen.getByLabelText("Tag name"), "Night");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(onCreate).toHaveBeenCalledWith("Night");
    expect(onValueChange).toHaveBeenCalledWith("3");
  });
});

describe("CategorySelect", () => {
  it("shows the selected category text instead of the raw value", () => {
    function Wrapper() {
      const [value, setValue] = useState("11");
      return (
        <CategorySelect
          categories={[makeCategory(10, "Nature", [makeCategory(11, "Mountains")])]}
          value={value}
          onValueChange={setValue}
          onCreate={vi.fn()}
        />
      );
    }

    render(<Wrapper />);

    expect(screen.getByText(/\s*Mountains$/)).toBeInTheDocument();
    expect(screen.queryByText(/^11$/)).not.toBeInTheDocument();
  });
});
