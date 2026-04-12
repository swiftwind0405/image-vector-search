export interface Tag {
  id: number;
  name: string;
  created_at: string;
  image_count: number | null;
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
  image_count: number | null;
}

export interface AlbumRule {
  id: number;
  album_id: number;
  tag_id: number;
  tag_name: string | null;
  match_mode: "include" | "exclude";
  created_at: string;
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
  embedding_status:
    | "embedded"
    | "skipped_oversized"
    | "failed"
    | "pending";
  created_at: string;
  updated_at: string;
  indexed?: boolean;
  indexed_content_hash?: string | null;
  file_url?: string;
}

export interface PurgeInactiveImagesRequest {
  content_hashes: string[];
}

export interface ImageRecordWithLabels extends ImageRecord {
  tags: Tag[];
  categories: Category[];
}

export interface Album {
  id: number;
  name: string;
  type: "manual" | "smart";
  description: string;
  rule_logic: "and" | "or" | null;
  source_paths: string[];
  image_count: number | null;
  cover_image: ImageRecordWithLabels | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedImages {
  items: ImageRecordWithLabels[];
  next_cursor: string | null;
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

export interface EmbeddingSettings {
  provider: string;
  jina_api_key_configured: boolean;
  google_api_key_configured: boolean;
  using_environment_fallback: boolean;
}

export interface UpdateEmbeddingSettingsRequest {
  provider: string;
  jina_api_key: string | null;
  google_api_key: string | null;
}

export interface FolderSettings {
  folders: string[];
  excluded: string[];
}

export interface UpdateExcludedFoldersRequest {
  excluded: string[];
}

export interface ForceEmbedImagesRequest {
  content_hashes: string[];
}
