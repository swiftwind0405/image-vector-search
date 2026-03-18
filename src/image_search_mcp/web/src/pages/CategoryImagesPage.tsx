import { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import ImageBrowser from "@/components/ImageBrowser";
import { useCategories } from "@/api/categories";
import type { CategoryNode } from "@/api/types";

function findCategoryNode(
  nodes: CategoryNode[],
  categoryId: number,
): CategoryNode | null {
  for (const node of nodes) {
    if (node.id === categoryId) {
      return node;
    }
    const match = findCategoryNode(node.children, categoryId);
    if (match) {
      return match;
    }
  }
  return null;
}

export default function CategoryImagesPage() {
  const { categoryId } = useParams();
  const parsedCategoryId = Number(categoryId);
  const { data: categories, isLoading } = useCategories();

  const category = useMemo(
    () => findCategoryNode(categories ?? [], parsedCategoryId),
    [categories, parsedCategoryId],
  );

  if (!Number.isInteger(parsedCategoryId) || parsedCategoryId <= 0) {
    return <p className="text-sm text-muted-foreground">Invalid category id.</p>;
  }

  return (
    <ImageBrowser
      title={category ? `Category: ${category.name}` : `Category #${parsedCategoryId}`}
      subtitle={
        isLoading
          ? "Loading category..."
          : "Includes images from this category and all descendant categories."
      }
      breadcrumb={
        <nav className="flex items-center gap-1 text-sm text-muted-foreground">
          <Link to="/categories" className="hover:text-foreground transition-colors">
            Categories
          </Link>
          <ChevronRight className="h-3.5 w-3.5" />
          <span className="text-foreground">
            {category ? category.name : `#${parsedCategoryId}`}
          </span>
        </nav>
      }
      queryScope={{ categoryId: parsedCategoryId, includeDescendants: true }}
      emptyMessage="No images are assigned to this category yet."
    />
  );
}
