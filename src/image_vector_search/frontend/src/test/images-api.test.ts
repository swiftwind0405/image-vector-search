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

  it("adds inactive, status, limit, and cursor filters", () => {
    expect(
      buildImagesPath({
        includeInactive: true,
        embeddingStatus: "skipped_oversized",
        limit: 200,
        cursor: "/data/images/01.jpg",
      }),
    ).toBe(
      "/api/images?include_inactive=true&embedding_status=skipped_oversized&limit=200&cursor=%2Fdata%2Fimages%2F01.jpg",
    );
  });
});
