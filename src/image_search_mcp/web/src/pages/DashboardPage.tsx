import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useStatus } from "@/api/status";
import { useJobs, useQueueJob } from "@/api/jobs";
import { apiFetch } from "@/api/client";
import type { SearchResult } from "@/api/types";
import { toast } from "sonner";

export default function DashboardPage() {
  const { data: status } = useStatus();
  const { data: jobs } = useJobs();
  const queueJob = useQueueJob();
  const [query, setQuery] = useState("");
  const [similarPath, setSimilarPath] = useState("");
  const [searchResults, setSearchResults] = useState<string>("");

  const handleTextSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/text",
        { method: "POST", body: JSON.stringify({ query, top_k: 5 }) },
      );
      setSearchResults(JSON.stringify(res, null, 2));
    } catch {
      toast.error("Search failed");
    }
  };

  const handleSimilarSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!similarPath.trim()) return;
    try {
      const res = await apiFetch<{ results: SearchResult[] }>(
        "/api/debug/search/similar",
        {
          method: "POST",
          body: JSON.stringify({ image_path: similarPath, top_k: 5 }),
        },
      );
      setSearchResults(JSON.stringify(res, null, 2));
    } catch {
      toast.error("Similar search failed");
    }
  };

  const handleQueueJob = (type: "incremental" | "rebuild") => {
    queueJob.mutate(type, {
      onSuccess: () => toast.success(`${type} job queued`),
      onError: () => toast.error("Failed to queue job"),
    });
  };

  const progress =
    status && status.images_on_disk > 0
      ? Math.round((status.active_images / status.images_on_disk) * 100)
      : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Index Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Index Overview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Indexing progress</span>
                <span>{progress}%</span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
            {status && (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-muted-foreground">On Disk</div>
                  <div className="text-lg font-medium">
                    {status.images_on_disk}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Indexed</div>
                  <div className="text-lg font-medium text-primary">
                    {status.active_images}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Inactive</div>
                  <div className="text-lg font-medium">
                    {status.inactive_images}
                  </div>
                </div>
                <div>
                  <div className="text-muted-foreground">Vectors</div>
                  <div className="text-lg font-medium">
                    {status.vector_entries}
                  </div>
                </div>
              </div>
            )}
            {status && (
              <p className="text-xs text-muted-foreground">
                {status.embedding_provider} / {status.embedding_model} /{" "}
                {status.embedding_version}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Index Control */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Index Control</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full"
              onClick={() => handleQueueJob("incremental")}
              disabled={queueJob.isPending}
            >
              Incremental Update
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => handleQueueJob("rebuild")}
              disabled={queueJob.isPending}
            >
              Full Rebuild
            </Button>
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {!jobs || jobs.length === 0 ? (
              <p className="text-sm text-muted-foreground">No jobs yet</p>
            ) : (
              <ul className="space-y-2">
                {jobs.slice(0, 10).map((job) => (
                  <li
                    key={job.id}
                    className="flex items-center justify-between text-sm"
                  >
                    <span>{job.job_type}</span>
                    <Badge variant="secondary">{job.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Debug Search */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Debug Search</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <form onSubmit={handleTextSearch} className="flex gap-2">
              <Input
                placeholder="Text query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <Button type="submit" variant="secondary">
                Search
              </Button>
            </form>
            <form onSubmit={handleSimilarSearch} className="flex gap-2">
              <Input
                placeholder="Image path for similar search..."
                value={similarPath}
                onChange={(e) => setSimilarPath(e.target.value)}
              />
              <Button type="submit" variant="secondary">
                Similar
              </Button>
            </form>
            {searchResults && (
              <pre className="bg-gray-950 text-gray-100 p-3 rounded-md text-xs overflow-auto max-h-64">
                {searchResults}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
