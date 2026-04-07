import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ImageOff, Tag, FolderTree, Ruler } from "lucide-react";
import type { SearchResult } from "@/api/types";

function ScoreBadge({ score }: { score: number }) {
  const pct = score * 100;
  const color =
    pct >= 80
      ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
      : pct >= 60
        ? "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30"
        : "bg-muted text-muted-foreground border-border";
  return (
    <span
      className={`inline-flex items-center rounded-md border px-1.5 py-0.5 text-[11px] font-mono font-semibold ${color}`}
    >
      {pct.toFixed(1)}%
    </span>
  );
}

interface Props {
  result: SearchResult;
  onClick?: () => void;
}

export default function SearchResultCard({ result, onClick }: Props) {
  const [imgError, setImgError] = useState(false);
  const filename = result.path.split("/").pop() ?? result.path;
  const dir = result.path.split("/").slice(0, -1).join("/");

  return (
    <div
      className="group relative cursor-pointer overflow-hidden rounded-[28px] border border-white/10 bg-card/75 p-3 shadow-curator transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/25 hover:bg-card"
      onClick={onClick}
    >
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-primary/10 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative flex gap-4">
      <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-[22px] border border-white/8 bg-muted">
        {imgError ? (
          <div className="flex h-full w-full items-center justify-center">
            <ImageOff className="h-6 w-6 text-muted-foreground/50" />
          </div>
        ) : (
          <img
            src={`/api/images/${result.content_hash}/file`}
            alt={filename}
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        )}
      </div>

      <div className="flex min-w-0 flex-1 flex-col justify-between py-1">
        <div className="space-y-1">
          <div className="flex items-start justify-between gap-2">
            <p className="truncate text-base font-medium text-white" title={result.path}>
              {filename}
            </p>
            <ScoreBadge score={result.score} />
          </div>
          {dir && (
            <p className="truncate text-xs text-muted-foreground" title={dir}>
              {dir}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1 rounded-full border border-white/8 bg-white/[0.03] px-2 py-1">
              <Ruler className="h-3 w-3" />
              {result.width} × {result.height}
            </span>
            <span className="rounded-full border border-white/8 bg-white/[0.03] px-2 py-1">{result.mime_type}</span>
          </div>
        </div>

        {(result.tags.length > 0 || result.categories.length > 0) && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            {result.tags.length > 0 && (
              <>
                <Tag className="h-3 w-3 text-muted-foreground shrink-0" />
                {result.tags.map((t) => (
                  <Badge key={t.id} variant="secondary" className="h-6 rounded-full border border-white/8 bg-white/[0.04] px-2 text-[10px] font-medium text-foreground">
                    {t.name}
                  </Badge>
                ))}
              </>
            )}
            {result.categories.length > 0 && (
              <>
                <FolderTree className="h-3 w-3 text-muted-foreground shrink-0 ml-1" />
                {result.categories.map((c) => (
                  <Badge key={c.id} variant="outline" className="h-6 rounded-full border-white/10 bg-transparent px-2 text-[10px] font-medium text-muted-foreground">
                    {c.name}
                  </Badge>
                ))}
              </>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
