import { X } from "lucide-react";
import type { Tag } from "@/api/types";

interface Props {
  tags: Tag[];
  activeTags: string[];
  onTagToggle: (name: string) => void;
  onClear: () => void;
}

export default function FilterBar({
  tags,
  activeTags,
  onTagToggle,
  onClear,
}: Props) {
  const hasActiveFilters = activeTags.length > 0;

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.08em] text-muted-foreground">Filters</p>
          <p className="mt-1 text-sm text-muted-foreground">Refine the visible archive by tag.</p>
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
                    : "inline-flex items-center gap-1 rounded-full border border-border bg-[#f9f9fa] px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
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
      </div>
    </div>
  );
}
