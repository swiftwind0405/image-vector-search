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
    <div className="rounded-[28px] border border-white/10 bg-card/65 p-4 shadow-curator backdrop-blur">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">Filters</p>
          <p className="mt-1 text-sm text-muted-foreground">Refine the visible archive by tag and top-level category.</p>
        </div>
        {hasActiveFilters && (
          <button
            onClick={onClear}
            className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
          >
            Clear all
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-sm">
      {tags.length > 0 && (
        <>
          <span className="font-medium text-muted-foreground">Tags:</span>
          {tags.map((tag) => {
            const active = activeTags.includes(tag.name);
            return (
              <button
                key={tag.id}
                onClick={() => onTagToggle(tag.name)}
                className={
                  active
                    ? "inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground shadow-sm"
                    : "inline-flex items-center gap-1 rounded-full border border-white/12 bg-white/[0.03] px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
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
          {tags.length > 0 && <span className="text-muted-foreground">/</span>}
          <span className="font-medium text-muted-foreground">Category:</span>
          {topLevelCategories.map((cat) => {
            const active = activeCategoryId === cat.id;
            return (
              <button
                key={cat.id}
                onClick={() => onCategoryToggle(cat.id)}
                className={
                  active
                    ? "inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground shadow-sm"
                    : "inline-flex items-center gap-1 rounded-full border border-white/12 bg-white/[0.03] px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
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
      </div>
    </div>
  );
}
