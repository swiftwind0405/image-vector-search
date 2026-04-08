import { Button } from "@/components/ui/button";
import { useStatus } from "@/api/status";
import { useJobs, useQueueJob } from "@/api/jobs";
import { useInactiveImages, usePurgeInactiveImages } from "@/api/images";
import { useQueryClient } from "@tanstack/react-query";
import { RefreshCw, Activity, Database, Images, TimerReset, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useEffect, useMemo, useState } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

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
  type QueueableJobType = "incremental" | "rebuild";

  const queryClient = useQueryClient();
  const { data: status, isFetching: statusFetching } = useStatus();
  const { data: jobs, isFetching: jobsFetching } = useJobs();
  const { data: inactiveImages, isLoading: inactiveImagesLoading } = useInactiveImages();
  const queueJob = useQueueJob();
  const purgeInactiveImages = usePurgeInactiveImages();
  const isRefreshing = statusFetching || jobsFetching;
  const [purgeDialogOpen, setPurgeDialogOpen] = useState(false);
  const [pendingJobType, setPendingJobType] = useState<QueueableJobType | null>(null);
  const [selectedInactiveHashes, setSelectedInactiveHashes] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!purgeDialogOpen || !inactiveImages) {
      return;
    }
    setSelectedInactiveHashes(new Set(inactiveImages.map((image) => image.content_hash)));
  }, [purgeDialogOpen, inactiveImages]);

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["status"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
  };

  const handleQueueJob = (type: QueueableJobType) => {
    queueJob.mutate(type, {
      onSuccess: () => toast.success(`${type} job queued`),
      onError: () => toast.error("Failed to queue job"),
    });
  };

  const pendingJobConfig = pendingJobType
    ? {
        incremental: {
          title: "Confirm Incremental Update",
          description:
            "Queue an incremental indexing job to scan for newly added, changed, or missing images without rebuilding the full collection.",
        },
        rebuild: {
          title: "Confirm Full Rebuild",
          description:
            "Queue a full rebuild job to recompute the entire index. Use this when the embedding stack changes or the collection needs a complete refresh.",
        },
      }[pendingJobType]
    : null;

  const progress =
    status && status.images_on_disk > 0
      ? Math.round((status.active_images / status.images_on_disk) * 100)
      : 0;
  const selectedInactiveCount = selectedInactiveHashes.size;
  const allInactiveSelected = !!inactiveImages?.length && selectedInactiveCount === inactiveImages.length;
  const purgeButtonLabel = selectedInactiveCount === 1 ? "Purge 1 Image" : `Purge ${selectedInactiveCount} Images`;
  const sortedSelectedHashes = useMemo(
    () => Array.from(selectedInactiveHashes).sort(),
    [selectedInactiveHashes],
  );

  const toggleInactiveHash = (contentHash: string, checked: boolean) => {
    setSelectedInactiveHashes((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(contentHash);
      } else {
        next.delete(contentHash);
      }
      return next;
    });
  };

  const handleToggleAllInactive = (checked: boolean) => {
    if (!inactiveImages) {
      return;
    }
    setSelectedInactiveHashes(
      checked ? new Set(inactiveImages.map((image) => image.content_hash)) : new Set(),
    );
  };

  const handlePurgeInactive = () => {
    purgeInactiveImages.mutate(
      { content_hashes: sortedSelectedHashes },
      {
        onSuccess: ({ affected }) => {
          toast.success(`Purged ${affected} inactive image${affected === 1 ? "" : "s"}`);
          queryClient.invalidateQueries({ queryKey: ["jobs"] });
          setPurgeDialogOpen(false);
        },
        onError: () => toast.error("Failed to purge inactive images"),
      },
    );
  };

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
                onClick={() => setPendingJobType("incremental")}
                disabled={queueJob.isPending}
              >
                Incremental Update
              </Button>
              <Button
                variant="outline"
                className="h-12 w-full justify-start rounded-2xl border-white/10 bg-white/[0.02] text-white hover:bg-white/[0.06]"
                onClick={() => setPendingJobType("rebuild")}
                disabled={queueJob.isPending}
              >
                Full Rebuild
              </Button>
              <Button
                variant="outline"
                className="h-12 w-full justify-start rounded-2xl border-white/10 bg-white/[0.02] text-white hover:bg-white/[0.06]"
                onClick={() => setPurgeDialogOpen(true)}
                disabled={!status?.inactive_images || purgeInactiveImages.isPending}
              >
                Purge Inactive
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

      <AlertDialog open={pendingJobType !== null} onOpenChange={(open) => !open && setPendingJobType(null)}>
        <AlertDialogContent className="border-white/10 bg-card text-white">
          <AlertDialogHeader>
            <AlertDialogTitle>{pendingJobConfig?.title}</AlertDialogTitle>
            <AlertDialogDescription>{pendingJobConfig?.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (!pendingJobType) {
                  return;
                }
                handleQueueJob(pendingJobType);
                setPendingJobType(null);
              }}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={purgeDialogOpen} onOpenChange={setPurgeDialogOpen}>
        <DialogContent className="flex max-h-[85vh] max-w-xl flex-col overflow-hidden border-white/10 bg-card text-white">
          <DialogHeader>
            <DialogTitle>Purge Inactive</DialogTitle>
            <DialogDescription>
              Remove selected inactive image metadata and vector entries. Source image files on disk are not deleted.
            </DialogDescription>
          </DialogHeader>

          {inactiveImagesLoading ? (
            <p className="text-sm text-muted-foreground">Loading inactive images…</p>
          ) : !inactiveImages?.length ? (
            <p className="text-sm text-muted-foreground">No inactive images available for purge.</p>
          ) : (
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
              <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <label className="flex items-center gap-3 text-sm font-medium text-white">
                  <Checkbox
                    aria-label="Select all inactive images"
                    checked={allInactiveSelected}
                    onCheckedChange={(checked) => handleToggleAllInactive(checked === true)}
                  />
                  Select all
                </label>
                <span className="text-xs text-muted-foreground">{selectedInactiveCount} selected</span>
              </div>

              <div className="space-y-2">
                {inactiveImages.map((image) => {
                  const checked = selectedInactiveHashes.has(image.content_hash);
                  return (
                    <label
                      key={image.content_hash}
                      className="flex w-full min-w-0 overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm"
                    >
                      <Checkbox
                        aria-label={image.canonical_path}
                        checked={checked}
                        onCheckedChange={(nextChecked) => toggleInactiveHash(image.content_hash, nextChecked === true)}
                      />
                      <span className="min-w-0 flex-1 overflow-hidden">
                        <span className="block overflow-hidden text-ellipsis whitespace-nowrap font-medium text-white">
                          {image.canonical_path}
                        </span>
                        <span className="block break-all text-xs text-muted-foreground">{image.content_hash}</span>
                      </span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setPurgeDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handlePurgeInactive}
              disabled={!selectedInactiveCount || purgeInactiveImages.isPending || !inactiveImages?.length}
            >
              {purgeButtonLabel}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
