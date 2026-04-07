import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { EmbeddingSettings, UpdateEmbeddingSettingsRequest } from "./types";

export function useEmbeddingSettings() {
  return useQuery({
    queryKey: ["settings", "embedding"],
    queryFn: () => apiFetch<EmbeddingSettings>("/api/settings/embedding"),
  });
}

export function useUpdateEmbeddingSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateEmbeddingSettingsRequest) =>
      apiFetch<EmbeddingSettings>("/api/settings/embedding", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "embedding"] });
      queryClient.invalidateQueries({ queryKey: ["status"] });
    },
  });
}
