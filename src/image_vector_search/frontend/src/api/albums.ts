import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { Album, AlbumRule, PaginatedImages } from "./types";

function invalidateAlbumQueries(qc: ReturnType<typeof useQueryClient>, albumId?: number) {
  qc.invalidateQueries({ queryKey: ["albums"] });
  if (albumId !== undefined) {
    qc.invalidateQueries({ queryKey: ["albums", albumId] });
    qc.invalidateQueries({ queryKey: ["albums", albumId, "images"] });
    qc.invalidateQueries({ queryKey: ["albums", albumId, "rules"] });
    qc.invalidateQueries({ queryKey: ["albums", albumId, "source-paths"] });
  }
}

export function useListAlbums() {
  return useQuery({
    queryKey: ["albums"],
    queryFn: () => apiFetch<Album[]>("/api/albums"),
  });
}

export function useAlbum(albumId: number) {
  return useQuery({
    queryKey: ["albums", albumId],
    queryFn: () => apiFetch<Album>(`/api/albums/${albumId}`),
    enabled: Number.isFinite(albumId) && albumId > 0,
  });
}

export function useAlbumImages(albumId: number, limit = 24) {
  return useInfiniteQuery({
    queryKey: ["albums", albumId, "images", limit],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      apiFetch<PaginatedImages>(
        `/api/albums/${albumId}/images?limit=${limit}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ""}`,
      ),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: Number.isFinite(albumId) && albumId > 0,
  });
}

export function useAlbumRules(albumId: number) {
  return useQuery({
    queryKey: ["albums", albumId, "rules"],
    queryFn: () => apiFetch<AlbumRule[]>(`/api/albums/${albumId}/rules`),
    enabled: Number.isFinite(albumId) && albumId > 0,
  });
}

export function useAlbumSourcePaths(albumId: number) {
  return useQuery({
    queryKey: ["albums", albumId, "source-paths"],
    queryFn: () => apiFetch<string[]>(`/api/albums/${albumId}/source-paths`),
    enabled: Number.isFinite(albumId) && albumId > 0,
  });
}

export function useCreateAlbum() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      name: string;
      type: "manual" | "smart";
      description?: string;
      rule_logic?: "and" | "or";
    }) =>
      apiFetch<Album>("/api/albums", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => invalidateAlbumQueries(qc),
  });
}

export function useUpdateAlbum() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      albumId,
      name,
      description,
    }: {
      albumId: number;
      name: string;
      description?: string;
    }) =>
      apiFetch<Album>(`/api/albums/${albumId}`, {
        method: "PUT",
        body: JSON.stringify({ name, description }),
      }),
    onSuccess: (_, variables) => invalidateAlbumQueries(qc, variables.albumId),
  });
}

export function useDeleteAlbum() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (albumId: number) =>
      apiFetch<void>(`/api/albums/${albumId}`, { method: "DELETE" }),
    onSuccess: (_, albumId) => invalidateAlbumQueries(qc, albumId),
  });
}

export function useAddImagesToAlbum() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      albumId,
      contentHashes,
    }: {
      albumId: number;
      contentHashes: string[];
    }) =>
      apiFetch<{ added: number }>(`/api/albums/${albumId}/images`, {
        method: "POST",
        body: JSON.stringify({ content_hashes: contentHashes }),
      }),
    onSuccess: (_, variables) => invalidateAlbumQueries(qc, variables.albumId),
  });
}

export function useRemoveImagesFromAlbum() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      albumId,
      contentHashes,
    }: {
      albumId: number;
      contentHashes: string[];
    }) =>
      apiFetch<{ removed: number }>(`/api/albums/${albumId}/images`, {
        method: "DELETE",
        body: JSON.stringify({ content_hashes: contentHashes }),
      }),
    onSuccess: (_, variables) => invalidateAlbumQueries(qc, variables.albumId),
  });
}

export function useSetAlbumRules() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      albumId,
      rules,
    }: {
      albumId: number;
      rules: Array<{ tag_id: number; match_mode: "include" | "exclude" }>;
    }) =>
      apiFetch<{ ok: boolean }>(`/api/albums/${albumId}/rules`, {
        method: "PUT",
        body: JSON.stringify({ rules }),
      }),
    onSuccess: (_, variables) => invalidateAlbumQueries(qc, variables.albumId),
  });
}

export function useSetAlbumSourcePaths() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      albumId,
      paths,
    }: {
      albumId: number;
      paths: string[];
    }) =>
      apiFetch<{ ok: boolean }>(`/api/albums/${albumId}/source-paths`, {
        method: "PUT",
        body: JSON.stringify({ paths }),
      }),
    onSuccess: (_, variables) => invalidateAlbumQueries(qc, variables.albumId),
  });
}
