import { describe, it, expect } from "vitest";
import { getDescendantIds } from "../utils/categories";
import type { CategoryNode } from "../api/types";

const makeNode = (id: number, name: string, children: CategoryNode[] = []): CategoryNode => ({
  id,
  name,
  parent_id: null,
  sort_order: 0,
  created_at: "2026-01-01T00:00:00",
  children,
});

describe("getDescendantIds", () => {
  it("returns [id] for a leaf node", () => {
    const tree = [makeNode(1, "Travel")];
    expect(getDescendantIds(tree, 1)).toEqual([1]);
  });

  it("returns parent id and all descendant ids", () => {
    const japan = makeNode(3, "Japan");
    const europe = makeNode(4, "Europe");
    const travel = makeNode(2, "Travel", [japan, europe]);
    const tree = [makeNode(1, "Work"), travel];

    const result = getDescendantIds(tree, 2);
    expect(result).toContain(2);
    expect(result).toContain(3);
    expect(result).toContain(4);
    expect(result).toHaveLength(3);
  });

  it("returns [] for non-existent id", () => {
    const tree = [makeNode(1, "Travel")];
    expect(getDescendantIds(tree, 99)).toEqual([]);
  });

  it("finds node at nested depth", () => {
    const child = makeNode(3, "Tokyo");
    const japan = makeNode(2, "Japan", [child]);
    const travel = makeNode(1, "Travel", [japan]);

    const result = getDescendantIds([travel], 2);
    expect(result).toEqual([2, 3]);
  });
});
