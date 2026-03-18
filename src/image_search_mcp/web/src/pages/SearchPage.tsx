import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { apiFetch } from "@/api/client";
import type { SearchResult } from "@/api/types";
import { toast } from "sonner";
import { Search, ScanSearch, FileImage, Ruler, Tag, FolderTree } from "lucide-react";

function ScoreBadge({ score }: { score: number }) {
  const pct = score * 100;
  const variant =
    pct >= 80 ? "default" : pct >= 60 ? "secondary" : "outline";
  return (
    <Badge variant={variant} className="text-xs font-mono">
      {pct.toFixed(1)}%
    </Badge>
  );
}

function ResultCard({ result }: { result: SearchResult }) {
  const filename = result.path.split("/").pop() ?? result.path;
  const dir = result.path.split("/").slice(0, -1).join("/");

  return (
    <Card className="flex flex-col gap-0 overflow-hidden">
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <CardTitle
              className="text-sm font-medium truncate"
              title={result.path}
            >
              <FileImage className="inline h-3.5 w-3.5 mr-1 text-muted-foreground" />
              {filename}
            </CardTitle>
            {dir && (
              <p
                className="text-xs text-muted-foreground truncate mt-0.5"
                title={dir}
              >
                {dir}
              </p>
            )}
          </div>
          <ScoreBadge score={result.score} />
        </div>
      </CardHeader>
      <CardContent className="px-4 pb-4 space-y-2">
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Ruler className="h-3 w-3" />
            {result.width} × {result.height}
          </span>
          <span>{result.mime_type}</span>
          <span
            className="font-mono text-[10px] truncate max-w-[120px]"
            title={result.content_hash}
          >
            {result.content_hash.slice(0, 12)}…
          </span>
        </div>

        {result.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <Tag className="h-3 w-3 text-muted-foreground self-center" />
            {result.tags.map((t) => (
              <Badge key={t.id} variant="secondary" className="text-xs h-5 px-1.5">
                {t.name}
              </Badge>
            ))}
          </div>
        )}

        {result.categories.length > 0 && (
          <div className="flex flex-wrap gap-1">
            <FolderTree className="h-3 w-3 text-muted-foreground self-center" />
            {result.categories.map((c) => (
              <Badge key={c.id} variant="outline" className="text-xs h-5 px-1.5">
                {c.name}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [similarPath, setSimilarPath] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchType, setSearchType] = useState<"text" | "similar" | null>(null);

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
      <h1 className="text-2xl font-semibold">Search</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Text Search */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Search className="h-4 w-4" />
              Text Search
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleTextSearch} className="flex gap-2">
              <Input
                placeholder="Describe an image..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={loading}
              />
              <Button type="submit" disabled={loading || !query.trim()}>
                Search
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Similar Image Search */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <ScanSearch className="h-4 w-4" />
              Similar Image
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSimilarSearch} className="flex gap-2">
              <Input
                placeholder="Image path..."
                value={similarPath}
                onChange={(e) => setSimilarPath(e.target.value)}
                disabled={loading}
              />
              <Button
                type="submit"
                variant="secondary"
                disabled={loading || !similarPath.trim()}
              >
                Similar
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* Results */}
      {loading && (
        <p className="text-sm text-muted-foreground animate-pulse">
          Searching…
        </p>
      )}

      {!loading && results !== null && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-medium text-muted-foreground">
              {results.length === 0
                ? "No results found"
                : `${results.length} result${results.length === 1 ? "" : "s"} — ${searchType === "text" ? `"${query}"` : similarPath}`}
            </h2>
          </div>
          {results.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {results.map((r) => (
                <ResultCard key={r.content_hash} result={r} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
