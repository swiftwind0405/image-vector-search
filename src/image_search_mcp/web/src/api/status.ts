import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { IndexStatus } from "./types";

export function useStatus() {
  return useQuery({
    queryKey: ["status"],
    queryFn: () => apiFetch<IndexStatus>("/api/status"),
    refetchInterval: 3000,
  });
}
