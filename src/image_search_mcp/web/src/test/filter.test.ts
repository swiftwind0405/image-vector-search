import { describe, it, expect } from "vitest";
import { getDescendantIds } from "../utils/categories";
import type { ImageRecordWithLabels, CategoryNode, Tag, Category } from "../api/types";

// Helper to build a minimal ImageRecordWithLabels
function makeImage(
  hash: string,
  opts: { tags?: Tag[]; categories?: Category[] } = {},
): ImageRecordWithLabels {
  const now = "2026-01-01T00:00:00";
  return {
    content_hash: hash,
    canonical_path: `/images/${hash}.jpg`,
    file_size: 1024,
    mtime: 0,
    mime_type: "image/jpeg",
    width: 100,
    height: 100,
    is_active: true,
    last_seen_at: now,
    embedding_provider: "fake",
    embedding_model: "fake",
    embedding_version: "v1",
    created_at: now,
    updated_at: now,
    tags: opts.tags ?? [],
    categories: opts.categories ?? [],
  };
}

function makeTag(id: number, name: string): Tag {
  return { id, name, created_at: "2026-01-01T00:00:00", image_count: null };
}

function makeCategory(id: number, name: string): Category {
  return { id, name, parent_id: null, sort_order: 0, created_at: "2026-01-01T00:00:00" };
}

function makeNode(id: number, name: string, children: CategoryNode[] = []): CategoryNode {
  return {
    id,
    name,
    parent_id: null,
    sort_order: 0,
    created_at: "2026-01-01T00:00:00",
    children,
    image_count: null,
  };
}

// The AND-filter logic extracted from ImagesPage
function applyFilter(
  images: ImageRecordWithLabels[],
  activeTags: string[],
  activeCategoryId: number | null,
  categoryTree: CategoryNode[],
): ImageRecordWithLabels[] {
  return images.filter((img) => {
    if (activeTags.length > 0) {
      const imageTagNames = img.tags.map((t) => t.name);
      if (!activeTags.every((name) => imageTagNames.includes(name))) return false;
    }
    if (activeCategoryId !== null) {
      const descendantIds = getDescendantIds(categoryTree, activeCategoryId);
      const imageCategoryIds = img.categories.map((c) => c.id);
      if (!imageCategoryIds.some((id) => descendantIds.includes(id))) return false;
    }
    return true;
  });
}

describe("AND-filter logic", () => {
  const nature = makeTag(1, "nature");
  const travel = makeTag(2, "travel");
  const travelCat = makeCategory(10, "Travel");
  const workCat = makeCategory(20, "Work");

  const imgA = makeImage("a", { tags: [nature, travel], categories: [travelCat] });
  const imgB = makeImage("b", { tags: [nature], categories: [workCat] });
  const imgC = makeImage("c", { tags: [travel] });
  const imgD = makeImage("d");

  const categoryTree = [makeNode(10, "Travel"), makeNode(20, "Work")];

  it("no filters: shows all images", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], [], null, categoryTree);
    expect(result).toHaveLength(4);
  });

  it("tag-only filter: returns only images with that tag", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["nature"], null, categoryTree);
    expect(result.map((i) => i.content_hash)).toEqual(["a", "b"]);
  });

  it("category-only filter: returns only images in that category", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], [], 10, categoryTree);
    expect(result.map((i) => i.content_hash)).toEqual(["a"]);
  });

  it("combined AND filter: tag AND category", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["nature"], 10, categoryTree);
    expect(result.map((i) => i.content_hash)).toEqual(["a"]);
  });

  it("combined AND filter: no match returns empty", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["travel"], 20, categoryTree);
    expect(result).toHaveLength(0);
  });
});
