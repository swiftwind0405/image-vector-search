import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/api/client";
import type { SearchResult, ImageRecordWithLabels } from "@/api/types";
import { toast } from "sonner";
import { ArrowRight, Compass, Image as ImageIcon } from "lucide-react";
import SearchResultCard from "@/components/SearchResultCard";
import ImageModal from "@/components/ImageModal";
import { cn } from "@/lib/utils";

function searchResultToImage(r: SearchResult): ImageRecordWithLabels {
  return {
    content_hash: r.content_hash,
    canonical_path: r.path,
    file_size: 0,
    mtime: 0,
    mime_type: r.mime_type,
    width: r.width,
    height: r.height,
    is_active: true,
    last_seen_at: "",
    embedding_provider: "",
    embedding_model: "",
    embedding_version: "",
    embedding_status: "embedded",
    created_at: "",
    updated_at: "",
    tags: r.tags,
    categories: r.categories,
  };
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [similarPath, setSimilarPath] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState<"text" | "similar" | null>(null);
  const [modalHash, setModalHash] = useState<string | null>(null);

  const imageList = useMemo(
    () => (results ?? []).map(searchResultToImage),
    [results],
  );

  const modalImage = modalHash
    ? imageList.find((img) => img.content_hash === modalHash) ?? null
    : null;

  const handleTextSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setSearchType("text");
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/text",
        { method: "POST", body: JSON.stringify({ query, top_k: 5 }) },
      );
      setResults(res.results);
    } catch {
      toast.error("Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleSimilarSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!similarPath.trim()) return;
    setLoading(true);
    setSearchType("similar");
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/similar",
        {
          method: "POST",
          body: JSON.stringify({ image_path: similarPath, top_k: 5 }),
        },
      );
      setResults(res.results);
    } catch {
      toast.error("Similar search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-[32px] border border-white/10 bg-card/78 p-5 shadow-curator backdrop-blur sm:p-6">
          <div className="grid gap-4 lg:grid-cols-2">
            <form onSubmit={handleTextSearch} className="rounded-[28px] border border-white/10 bg-white/[0.035] p-4">
              <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                <Compass className="h-4 w-4 text-primary" />
                Text Search
              </div>
              <p className="mb-4 text-sm leading-6 text-muted-foreground">
                Describe what should appear in the frame and let semantic search retrieve the closest indexed matches.
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="Describe an image..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={loading}
                  className="h-11 rounded-2xl border-white/10 bg-white/[0.03]"
                />
                <Button type="submit" disabled={loading || !query.trim()} className="h-11 rounded-2xl px-4">
                  Search
                </Button>
              </div>
            </form>

            <form onSubmit={handleSimilarSearch} className="rounded-[28px] border border-white/10 bg-white/[0.035] p-4">
              <div className="mb-4 flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                <ImageIcon className="h-4 w-4 text-primary" />
                Similar Image
              </div>
              <p className="mb-4 text-sm leading-6 text-muted-foreground">
                Point to a local file path to retrieve visually adjacent frames from the archive.
              </p>
              <div className="flex gap-2">
                <Input
                  placeholder="/path/to/image.jpg"
                  value={similarPath}
                  onChange={(e) => setSimilarPath(e.target.value)}
                  disabled={loading}
                  className="h-11 rounded-2xl border-white/10 bg-white/[0.03]"
                />
                <Button
                  type="submit"
                  variant="secondary"
                  disabled={loading || !similarPath.trim()}
                  className="h-11 rounded-2xl border-white/10 bg-white/[0.06] text-white hover:bg-white/[0.1]"
                >
                  Similar
                </Button>
              </div>
            </form>
          </div>
        </div>

        <aside className="rounded-[32px] border border-white/10 bg-card/72 p-5 shadow-curator backdrop-blur">
          <p className="text-[11px] uppercase tracking-[0.22em] text-primary/90">Search Rhythm</p>
          <div className="mt-4 space-y-4 text-sm leading-6 text-muted-foreground">
            <p>Use text mode when the target is semantic or descriptive.</p>
            <p>Use similar mode when you already have a frame and want visual neighbors.</p>
            <p className="flex items-center gap-2 text-white">
              <ArrowRight className="h-4 w-4 text-primary" />
              Results open into the same review lightbox used across the archive.
            </p>
          </div>
        </aside>
      </section>

      {loading && (
        <p className="text-sm text-muted-foreground animate-pulse">
          Searching…
        </p>
      )}

      {!loading && results !== null && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-2 rounded-[28px] border border-white/10 bg-card/65 px-4 py-3 shadow-curator backdrop-blur">
            <h2 className="text-sm font-medium text-muted-foreground">
              {results.length === 0
                ? "No results found"
                : `${results.length} result${results.length === 1 ? "" : "s"} — ${searchType === "text" ? `"${query}"` : similarPath}`}
            </h2>
            <span
              className={cn(
                "rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.18em]",
                searchType === "text" ? "bg-primary/15 text-primary" : "bg-white/[0.05] text-white",
              )}
            >
              {searchType === "text" ? "Text mode" : "Similar mode"}
            </span>
          </div>
          {results.length > 0 && (
            <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
              {results.map((r) => (
                <SearchResultCard
                  key={r.content_hash}
                  result={r}
                  onClick={() => setModalHash(r.content_hash)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <ImageModal
        image={modalImage}
        images={imageList}
        open={modalHash !== null}
        onClose={() => setModalHash(null)}
        onNavigate={(hash) => setModalHash(hash)}
      />
    </div>
  );
}
