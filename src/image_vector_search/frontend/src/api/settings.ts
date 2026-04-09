import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  EmbeddingSettings,
  UpdateEmbeddingSettingsRequest,
  FolderSettings,
  UpdateExcludedFoldersRequest,
} from "./types";

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

export function useFolderSettings() {
  return useQuery({
    queryKey: ["settings", "folders"],
    queryFn: () => apiFetch<FolderSettings>("/api/settings/folders"),
  });
}

export function useUpdateExcludedFolders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateExcludedFoldersRequest) =>
      apiFetch<FolderSettings>("/api/settings/excluded-folders", {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "folders"] });
      queryClient.invalidateQueries({ queryKey: ["status"] });
    },
  });
}
