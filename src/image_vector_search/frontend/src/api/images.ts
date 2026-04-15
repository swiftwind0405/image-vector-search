import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { apiFetch } from "./client";
import type {
  BulkResponse,
  ForceEmbedImagesRequest,
  ImageRecord,
  PaginatedImages,
  PurgeInactiveImagesRequest,
  Tag,
} from "./types";

export interface ImagesQueryOptions {
  folder?: string;
  tagId?: number;
  includeInactive?: boolean;
  embeddingStatus?: string;
  limit?: number;
  cursor?: string;
}

export function buildImagesPath(options: ImagesQueryOptions = {}) {
  const params = new URLSearchParams();
  if (options.folder) {
    params.set("folder", options.folder);
  }
  if (options.tagId !== undefined) {
    params.set("tag_id", String(options.tagId));
  }
  if (options.includeInactive !== undefined) {
    params.set("include_inactive", String(options.includeInactive));
  }
  if (options.embeddingStatus) {
    params.set("embedding_status", options.embeddingStatus);
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options.cursor) {
    params.set("cursor", options.cursor);
  }
  const query = params.toString();
  return query ? `/api/images?${query}` : "/api/images";
}

export function useImages(options: ImagesQueryOptions = {}) {
  return useQuery({
    queryKey: [
      "images",
      options.folder ?? "all",
      options.tagId ?? null,
      options.includeInactive ?? false,
      options.embeddingStatus ?? null,
      options.limit ?? null,
      options.cursor ?? null,
    ],
    queryFn: async () =>
      (await apiFetch<PaginatedImages>(buildImagesPath(options))).items,
  });
}

export function useImagesInfinite(options: ImagesQueryOptions = {}) {
  return useInfiniteQuery({
    queryKey: [
      "images",
      "infinite",
      options.folder ?? "all",
      options.tagId ?? null,
      options.includeInactive ?? false,
      options.embeddingStatus ?? null,
      options.limit ?? 200,
    ],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      apiFetch<PaginatedImages>(
        buildImagesPath({
          ...options,
          limit: options.limit ?? 200,
          cursor: pageParam,
        }),
      ),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  });
}

export function useFilesystemImages(limit?: number) {
  return useQuery({
    queryKey: ["images", "filesystem", limit ?? null],
    queryFn: async () =>
      await apiFetch<PaginatedImages>(
        limit !== undefined
          ? `/api/images/filesystem?limit=${limit}`
          : "/api/images/filesystem",
      ),
  });
}

export function useInactiveImages() {
  return useQuery({
    queryKey: ["images", "inactive"],
    queryFn: () => apiFetch<ImageRecord[]>("/api/images/inactive"),
  });
}

export function usePurgeInactiveImages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PurgeInactiveImagesRequest) =>
      apiFetch<BulkResponse>("/api/images/inactive/purge", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images", "inactive"] });
      qc.invalidateQueries({ queryKey: ["status"] });
    },
  });
}

export function useOversizedImages() {
  return useQuery({
    queryKey: ["images", "oversized"],
    queryFn: () => apiFetch<ImageRecord[]>("/api/images/oversized"),
  });
}

export function useForceEmbedImages() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ForceEmbedImagesRequest) =>
      apiFetch("/api/images/oversized/embed", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["images"] });
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["status"] });
    },
  });
}

export function useImageTags(contentHash: string) {
  return useQuery({
    queryKey: ["images", contentHash, "tags"],
    queryFn: () => apiFetch<Tag[]>(`/api/images/${contentHash}/tags`),
    enabled: !!contentHash,
  });
}

export function useAddTagToImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      tagId,
    }: {
      contentHash: string;
      tagId: number;
    }) =>
      apiFetch(`/api/images/${contentHash}/tags`, {
        method: "POST",
        body: JSON.stringify({ tag_id: tagId }),
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({ queryKey: ["images", contentHash, "tags"] });
    },
  });
}

export function useRemoveTagFromImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      tagId,
    }: {
      contentHash: string;
      tagId: number;
    }) =>
      apiFetch<void>(`/api/images/${contentHash}/tags/${tagId}`, {
        method: "DELETE",
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({ queryKey: ["images", contentHash, "tags"] });
    },
  });
}
