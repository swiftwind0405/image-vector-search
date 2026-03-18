import type { CategoryNode } from "../api/types";

export function getDescendantIds(tree: CategoryNode[], categoryId: number): number[] {
  for (const node of tree) {
    if (node.id === categoryId) {
      return collectIds(node);
    }
    const found = getDescendantIds(node.children, categoryId);
    if (found.length > 0) {
      return found;
    }
  }
  return [];
}

function collectIds(node: CategoryNode): number[] {
  const ids: number[] = [node.id];
  for (const child of node.children) {
    ids.push(...collectIds(child));
  }
  return ids;
}
