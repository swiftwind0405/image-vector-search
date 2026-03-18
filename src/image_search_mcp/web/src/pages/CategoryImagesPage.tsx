import { useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
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
  const navigate = useNavigate();
  const parsedCategoryId = Number(categoryId);
  const { data: categories } = useCategories();

  const category = useMemo(
    () => findCategoryNode(categories ?? [], parsedCategoryId),
    [categories, parsedCategoryId],
  );

  if (!Number.isInteger(parsedCategoryId) || parsedCategoryId <= 0) {
    return <p className="text-sm text-muted-foreground">Invalid category id.</p>;
  }

  const displayName = category ? category.name : `Category #${parsedCategoryId}`;

  return (
    <ImageBrowser
      title={displayName}
      breadcrumb={
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 gap-1 text-muted-foreground"
            onClick={() => navigate("/categories")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <h1 className="text-lg font-semibold">{displayName}</h1>
        </div>
      }
      hideTitle
      queryScope={{ categoryId: parsedCategoryId, includeDescendants: true }}
      emptyMessage="No images are assigned to this category yet."
    />
  );
}
