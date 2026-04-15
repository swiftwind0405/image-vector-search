import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { BulkResponse } from "./types";

export function useFolders() {
  return useQuery({
    queryKey: ["folders"],
    queryFn: () => apiFetch<string[]>("/api/folders"),
  });
}

export function useBulkAddTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      content_hashes,
      tag_id,
    }: {
      content_hashes: string[];
      tag_id: number;
    }) =>
      apiFetch<BulkResponse>("/api/bulk/tags/add", {
        method: "POST",
        body: JSON.stringify({ content_hashes, tag_id }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["images"] }),
  });
}

export function useBulkRemoveTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      content_hashes,
      tag_id,
    }: {
      content_hashes: string[];
      tag_id: number;
    }) =>
      apiFetch<BulkResponse>("/api/bulk/tags/remove", {
        method: "POST",
        body: JSON.stringify({ content_hashes, tag_id }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["images"] }),
  });
}

export function useBulkFolderAddTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      folder,
      tag_id,
    }: {
      folder: string;
      tag_id: number;
    }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/tags/add", {
        method: "POST",
        body: JSON.stringify({ folder, tag_id }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["images"] }),
  });
}

export function useBulkFolderRemoveTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      folder,
      tag_id,
    }: {
      folder: string;
      tag_id: number;
    }) =>
      apiFetch<BulkResponse>("/api/bulk/folder/tags/remove", {
        method: "POST",
        body: JSON.stringify({ folder, tag_id }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["images"] }),
  });
}

export function useOpenFile() {
  return useMutation({
    mutationFn: ({ path }: { path: string }) =>
      apiFetch<{ ok: boolean }>("/api/files/open", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
  });
}

export function useRevealFile() {
  return useMutation({
    mutationFn: ({ path }: { path: string }) =>
      apiFetch<{ ok: boolean }>("/api/files/reveal", {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
  });
}
