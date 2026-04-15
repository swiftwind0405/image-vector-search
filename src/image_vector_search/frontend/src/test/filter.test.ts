import { describe, it, expect } from "vitest";
import type { ImageRecordWithLabels, Tag } from "../api/types";

// Helper to build a minimal ImageRecordWithLabels
function makeImage(
  hash: string,
  opts: { tags?: Tag[] } = {},
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
    embedding_status: "embedded",
    created_at: now,
    updated_at: now,
    tags: opts.tags ?? [],
  };
}

function makeTag(id: number, name: string): Tag {
  return { id, name, created_at: "2026-01-01T00:00:00", image_count: null };
}

function applyFilter(
  images: ImageRecordWithLabels[],
  activeTags: string[],
): ImageRecordWithLabels[] {
  return images.filter((img) => {
    if (activeTags.length > 0) {
      const imageTagNames = img.tags.map((t) => t.name);
      if (!activeTags.every((name) => imageTagNames.includes(name))) return false;
    }
    return true;
  });
}

describe("tag filter logic", () => {
  const nature = makeTag(1, "nature");
  const travel = makeTag(2, "travel");

  const imgA = makeImage("a", { tags: [nature, travel] });
  const imgB = makeImage("b", { tags: [nature] });
  const imgC = makeImage("c", { tags: [travel] });
  const imgD = makeImage("d");

  it("no filters: shows all images", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], []);
    expect(result).toHaveLength(4);
  });

  it("tag-only filter: returns only images with that tag", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["nature"]);
    expect(result.map((i) => i.content_hash)).toEqual(["a", "b"]);
  });

  it("multiple tags use AND semantics", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["nature", "travel"]);
    expect(result.map((i) => i.content_hash)).toEqual(["a"]);
  });

  it("non-matching tags return empty", () => {
    const result = applyFilter([imgA, imgB, imgC, imgD], ["travel", "missing"]);
    expect(result).toHaveLength(0);
  });
});
