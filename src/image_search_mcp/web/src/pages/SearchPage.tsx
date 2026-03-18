import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiFetch } from "@/api/client";
import type { SearchResult, ImageRecordWithLabels } from "@/api/types";
import { toast } from "sonner";
import { Search, ScanSearch } from "lucide-react";
import SearchResultCard from "@/components/SearchResultCard";
import ImageModal from "@/components/ImageModal";

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
                placeholder="/path/to/image.jpg"
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
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
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
