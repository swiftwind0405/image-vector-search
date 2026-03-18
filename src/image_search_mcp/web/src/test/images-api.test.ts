import { describe, it, expect } from "vitest";
import { buildImagesPath } from "../api/images";

describe("buildImagesPath", () => {
  it("returns the base images endpoint when no filters are provided", () => {
    expect(buildImagesPath()).toBe("/api/images");
  });

  it("adds a tag scope", () => {
    expect(buildImagesPath({ tagId: 7 })).toBe("/api/images?tag_id=7");
  });

  it("adds category scope with descendant toggle", () => {
    expect(buildImagesPath({ categoryId: 11, includeDescendants: true })).toBe(
      "/api/images?category_id=11&include_descendants=true",
    );
  });

  it("combines folder and tag filters", () => {
    expect(buildImagesPath({ folder: "nature", tagId: 7 })).toBe(
      "/api/images?folder=nature&tag_id=7",
    );
  });
});
