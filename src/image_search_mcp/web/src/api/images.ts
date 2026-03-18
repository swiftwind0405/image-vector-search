import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { ImageRecordWithLabels, Tag, Category } from "./types";

export interface ImagesQueryOptions {
  folder?: string;
  tagId?: number;
  categoryId?: number;
  includeDescendants?: boolean;
}

export function buildImagesPath(options: ImagesQueryOptions = {}) {
  const params = new URLSearchParams();
  if (options.folder) {
    params.set("folder", options.folder);
  }
  if (options.tagId !== undefined) {
    params.set("tag_id", String(options.tagId));
  }
  if (options.categoryId !== undefined) {
    params.set("category_id", String(options.categoryId));
    params.set(
      "include_descendants",
      String(options.includeDescendants ?? true),
    );
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
      options.categoryId ?? null,
      options.includeDescendants ?? true,
    ],
    queryFn: () => apiFetch<ImageRecordWithLabels[]>(buildImagesPath(options)),
  });
}

export function useImageTags(contentHash: string) {
  return useQuery({
    queryKey: ["images", contentHash, "tags"],
    queryFn: () => apiFetch<Tag[]>(`/api/images/${contentHash}/tags`),
    enabled: !!contentHash,
  });
}

export function useImageCategories(contentHash: string) {
  return useQuery({
    queryKey: ["images", contentHash, "categories"],
    queryFn: () =>
      apiFetch<Category[]>(`/api/images/${contentHash}/categories`),
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

export function useAddCategoryToImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      categoryId,
    }: {
      contentHash: string;
      categoryId: number;
    }) =>
      apiFetch(`/api/images/${contentHash}/categories`, {
        method: "POST",
        body: JSON.stringify({ category_id: categoryId }),
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({
        queryKey: ["images", contentHash, "categories"],
      });
    },
  });
}

export function useRemoveCategoryFromImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      contentHash,
      categoryId,
    }: {
      contentHash: string;
      categoryId: number;
    }) =>
      apiFetch<void>(`/api/images/${contentHash}/categories/${categoryId}`, {
        method: "DELETE",
      }),
    onSuccess: (_, { contentHash }) => {
      qc.invalidateQueries({
        queryKey: ["images", contentHash, "categories"],
      });
    },
  });
}
