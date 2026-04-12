import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { ImageRecord } from "./types";

export interface FolderBrowseResponse {
  path: string;
  parent: string | null;
  folders: string[];
  images: ImageRecord[];
  next_cursor: string | null;
}

export function buildFolderBrowsePath(path: string) {
  const params = new URLSearchParams();
  if (path !== "") {
    params.set("path", path);
  }
  const query = params.toString();
  return query ? `/api/folders/browse?${query}` : "/api/folders/browse";
}

export function useFolderBrowse(path: string) {
  return useQuery({
    queryKey: ["folders", "browse", path],
    queryFn: () => apiFetch<FolderBrowseResponse>(buildFolderBrowsePath(path)),
  });
}
