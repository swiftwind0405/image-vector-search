export interface Tag {
  id: number;
  name: string;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
}

export interface CategoryNode extends Category {
  children: CategoryNode[];
}

export interface ImageRecord {
  content_hash: string;
  canonical_path: string;
  file_size: number;
  mtime: number;
  mime_type: string;
  width: number;
  height: number;
  is_active: boolean;
  last_seen_at: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_version: string;
  created_at: string;
  updated_at: string;
}

export interface IndexStatus {
  images_on_disk: number;
  total_images: number;
  active_images: number;
  inactive_images: number;
  vector_entries: number;
  embedding_provider: string;
  embedding_model: string;
  embedding_version: string;
  last_incremental_update_at: string | null;
  last_full_rebuild_at: string | null;
  last_error_summary: string | null;
}

export interface JobRecord {
  id: string;
  job_type: string;
  status: string;
  requested_at: string;
  started_at: string | null;
  finished_at: string | null;
  summary_json: string | null;
  error_text: string | null;
}

export interface SearchResult {
  content_hash: string;
  path: string;
  score: number;
  width: number;
  height: number;
  mime_type: string;
  tags: Tag[];
  categories: Category[];
}

export interface BulkResponse {
  ok: boolean;
  affected: number;
}
