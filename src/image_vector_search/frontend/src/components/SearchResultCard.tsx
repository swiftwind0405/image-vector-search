import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ImageOff, Tag, Ruler } from "lucide-react";
import type { SearchResult } from "@/api/types";

function ScoreBadge({ score }: { score: number }) {
  const pct = score * 100;
  const color =
    pct >= 80
      ? "bg-[#ecfdf3] text-emerald-700 dark:text-emerald-400 border-emerald-500/30"
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
      className="group relative cursor-pointer overflow-hidden rounded-lg border border-border bg-card p-3 transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/25 hover:bg-card"
      onClick={onClick}
    >
      <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-primary/10 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="relative flex gap-4">
      <div className="relative h-28 w-28 shrink-0 overflow-hidden rounded-md border border-border bg-muted">
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
            <p className="truncate text-base font-medium text-foreground" title={result.path}>
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
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-[#f9f9fa] px-2 py-1">
              <Ruler className="h-3 w-3" />
              {result.width} × {result.height}
            </span>
            <span className="rounded-full border border-border bg-[#f9f9fa] px-2 py-1">{result.mime_type}</span>
          </div>
        </div>

        {result.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-1.5">
            <Tag className="h-3 w-3 text-muted-foreground shrink-0" />
            {result.tags.map((t) => (
              <Badge key={t.id} variant="secondary" className="h-6 rounded-full border border-border bg-[#f7f7f8] px-2 text-[10px] font-medium text-foreground">
                {t.name}
              </Badge>
            ))}
          </div>
        )}
      </div>
      </div>
    </div>
  );
}
