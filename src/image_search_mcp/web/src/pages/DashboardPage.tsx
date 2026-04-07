import { Button } from "@/components/ui/button";
import { useStatus } from "@/api/status";
import { useJobs, useQueueJob } from "@/api/jobs";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Activity, Database, Images, TimerReset, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

function StatPanel({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  hint: string;
  icon: typeof Images;
}) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-card/75 p-5 shadow-curator backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">{label}</p>
          <p className="text-3xl font-semibold tracking-tight text-white">{value}</p>
          <p className="text-sm text-muted-foreground">{hint}</p>
        </div>
        <div className="rounded-2xl bg-primary/12 p-3 text-primary">
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: status, isFetching: statusFetching } = useStatus();
  const { data: jobs, isFetching: jobsFetching } = useJobs();
  const queueJob = useQueueJob();
  const isRefreshing = statusFetching || jobsFetching;

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["status"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
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
      <div className="flex items-center justify-between">
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="ml-auto border-white/10 bg-white/[0.03] text-white hover:bg-white/[0.06]"
        >
          <RefreshCw className={`h-4 w-4 mr-1.5 ${isRefreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <section className="grid gap-4 xl:grid-cols-[1.4fr_0.95fr]">
        <div className="overflow-hidden rounded-[32px] border border-white/10 bg-card/80 p-6 shadow-curator backdrop-blur">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="space-y-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-primary/90">Collection Overview</p>
              <div className="space-y-3">
                <div className="flex items-end gap-4">
                  <span className="text-6xl font-semibold tracking-tight text-white">{progress}%</span>
                  <span className="pb-2 text-sm text-muted-foreground">index coverage</span>
                </div>
                <p className="max-w-xl text-sm leading-6 text-muted-foreground">
                  Active embeddings cover most of the archive. Use this page to monitor drift, confirm model configuration, and trigger rebuilds when the collection changes.
                </p>
              </div>
            </div>

            <div className="rounded-[28px] border border-primary/20 bg-primary/10 p-5 lg:w-[320px]">
              <div className="flex items-center gap-2 text-primary">
                <Sparkles className="h-4 w-4" />
                <span className="text-xs uppercase tracking-[0.2em]">Embedding stack</span>
              </div>
              {status && (
                <div className="mt-4 space-y-2 text-sm">
                  <p className="font-medium text-white">{status.embedding_provider}</p>
                  <p className="text-muted-foreground">{status.embedding_model}</p>
                  <p className="text-xs text-muted-foreground">Version {status.embedding_version}</p>
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 h-3 overflow-hidden rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-primary transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>

          {status && (
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <StatPanel label="On Disk" value={status.images_on_disk} hint="Frames currently detected on the source volume." icon={Images} />
              <StatPanel label="Indexed" value={status.active_images} hint="Assets available for semantic retrieval." icon={Database} />
              <StatPanel label="Inactive" value={status.inactive_images} hint="Files known to metadata but not active in the search set." icon={TimerReset} />
            </div>
          )}
        </div>

        <div className="grid gap-4">
          <div className="rounded-[28px] border border-white/10 bg-card/72 p-5 shadow-curator backdrop-blur">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
              <Activity className="h-4 w-4 text-primary" />
              Actions
            </div>
            <div className="mt-5 space-y-3">
              <Button
                className="h-12 w-full justify-start rounded-2xl text-sm"
                onClick={() => handleQueueJob("incremental")}
                disabled={queueJob.isPending}
              >
                Incremental Update
              </Button>
              <Button
                variant="outline"
                className="h-12 w-full justify-start rounded-2xl border-white/10 bg-white/[0.02] text-white hover:bg-white/[0.06]"
                onClick={() => handleQueueJob("rebuild")}
                disabled={queueJob.isPending}
              >
                Full Rebuild
              </Button>
            </div>
          </div>

          <div className="rounded-[28px] border border-white/10 bg-card/72 p-5 shadow-curator backdrop-blur">
            <div className="flex items-center justify-between">
              <p className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">Recent Activity</p>
              <span className="text-xs text-muted-foreground">{jobs?.length ?? 0} jobs</span>
            </div>
            <div className="mt-5 space-y-3">
              {!jobs || jobs.length === 0 ? (
                <p className="text-sm text-muted-foreground">No jobs yet</p>
              ) : (
                jobs.slice(0, 10).map((job, index) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between gap-3 rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium capitalize text-white">{job.job_type}</p>
                      <p className="text-xs text-muted-foreground">Queue item {index + 1}</p>
                    </div>
                    <span
                      className={cn(
                        "rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.18em]",
                        job.status === "completed"
                          ? "bg-emerald-500/15 text-emerald-300"
                          : job.status === "failed"
                            ? "bg-red-500/15 text-red-300"
                            : "bg-primary/15 text-primary",
                      )}
                    >
                      {job.status}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
