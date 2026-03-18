import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { JobRecord } from "./types";

export function useJobs() {
  return useQuery({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<JobRecord[]>("/api/jobs"),
  });
}

export function useQueueJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobType: "incremental" | "rebuild") =>
      apiFetch<JobRecord>(`/api/jobs/${jobType}`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["status"] });
    },
  });
}
