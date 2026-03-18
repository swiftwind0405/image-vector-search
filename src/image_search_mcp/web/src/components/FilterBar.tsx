import { X } from "lucide-react";
import type { Tag, CategoryNode } from "@/api/types";

interface Props {
  tags: Tag[];
  categories: CategoryNode[];
  activeTags: string[];
  activeCategoryId: number | null;
  onTagToggle: (name: string) => void;
  onCategoryToggle: (id: number) => void;
  onClear: () => void;
}

export default function FilterBar({
  tags,
  categories,
  activeTags,
  activeCategoryId,
  onTagToggle,
  onCategoryToggle,
  onClear,
}: Props) {
  const hasActiveFilters = activeTags.length > 0 || activeCategoryId !== null;
  const topLevelCategories = categories;

  return (
    <div className="flex flex-wrap items-center gap-2 py-2 text-sm">
      {tags.length > 0 && (
        <>
          <span className="text-muted-foreground font-medium">Tags:</span>
          {tags.map((tag) => {
            const active = activeTags.includes(tag.name);
            return (
              <button
                key={tag.id}
                onClick={() => onTagToggle(tag.name)}
                className={
                  active
                    ? "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-primary text-primary-foreground"
                    : "inline-flex items-center gap-1 rounded-full border border-dashed px-2.5 py-0.5 text-xs font-medium text-muted-foreground hover:border-solid hover:text-foreground"
                }
              >
                {active && <X className="h-3 w-3" />}
                {!active && <span>+</span>}
                {tag.name}
              </button>
            );
          })}
        </>
      )}

      {topLevelCategories.length > 0 && (
        <>
          {tags.length > 0 && <span className="text-muted-foreground">│</span>}
          <span className="text-muted-foreground font-medium">Category:</span>
          {topLevelCategories.map((cat) => {
            const active = activeCategoryId === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onCategoryToggle(cat.id)}
                className={
                  active
                    ? "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium bg-primary text-primary-foreground"
                    : "inline-flex items-center gap-1 rounded-full border border-dashed px-2.5 py-0.5 text-xs font-medium text-muted-foreground hover:border-solid hover:text-foreground"
                }
              >
                {active && <X className="h-3 w-3" />}
                {!active && <span>+</span>}
                {cat.name}
              </button>
            );
          })}
        </>
      )}

      {hasActiveFilters && (
        <button
          onClick={onClear}
          className="ml-auto text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
