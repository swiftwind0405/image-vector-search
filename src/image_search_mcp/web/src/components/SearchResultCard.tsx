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
      className="group relative flex gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-accent/50 cursor-pointer"
      onClick={onClick}
    >
      {/* Thumbnail */}
      <div className="relative h-24 w-24 shrink-0 rounded-md overflow-hidden bg-muted">
        {imgError ? (
          <div className="flex h-full w-full items-center justify-center">
            <ImageOff className="h-6 w-6 text-muted-foreground/50" />
          </div>
        ) : (
          <img
            src={`/api/images/${result.content_hash}/file`}
            alt={filename}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        )}
      </div>

      {/* Details */}
      <div className="flex min-w-0 flex-1 flex-col justify-between py-0.5">
        <div className="space-y-1">
          <div className="flex items-start justify-between gap-2">
            <p className="text-sm font-medium truncate" title={result.path}>
              {filename}
            </p>
            <ScoreBadge score={result.score} />
          </div>
          {dir && (
            <p className="text-xs text-muted-foreground truncate" title={dir}>
              {dir}
            </p>
          )}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Ruler className="h-3 w-3" />
              {result.width} × {result.height}
            </span>
            <span>{result.mime_type}</span>
          </div>
        </div>

        {/* Tags & Categories */}
        {(result.tags.length > 0 || result.categories.length > 0) && (
          <div className="flex flex-wrap items-center gap-1 mt-1.5">
            {result.tags.length > 0 && (
              <>
                <Tag className="h-3 w-3 text-muted-foreground shrink-0" />
                {result.tags.map((t) => (
                  <Badge key={t.id} variant="secondary" className="text-[10px] h-[18px] px-1.5">
                    {t.name}
                  </Badge>
                ))}
              </>
            )}
            {result.categories.length > 0 && (
              <>
                <FolderTree className="h-3 w-3 text-muted-foreground shrink-0 ml-1" />
                {result.categories.map((c) => (
                  <Badge key={c.id} variant="outline" className="text-[10px] h-[18px] px-1.5">
                    {c.name}
                  </Badge>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
