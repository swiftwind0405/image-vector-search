import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { ImageRecord, Tag, Category } from "./types";

export function useImages() {
  return useQuery({
    queryKey: ["images"],
    queryFn: () => apiFetch<ImageRecord[]>("/api/images"),
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
