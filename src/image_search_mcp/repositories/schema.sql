CREATE TABLE IF NOT EXISTS images (
  content_hash TEXT PRIMARY KEY,
  canonical_path TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  mtime REAL NOT NULL,
  mime_type TEXT NOT NULL,
  width INTEGER NOT NULL,
  height INTEGER NOT NULL,
  is_active INTEGER NOT NULL,
  last_seen_at TEXT NOT NULL,
  embedding_provider TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS image_paths (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_hash TEXT NOT NULL REFERENCES images(content_hash),
  path TEXT NOT NULL UNIQUE,
  file_size INTEGER NOT NULL,
  mtime REAL NOT NULL,
  is_active INTEGER NOT NULL,
  last_seen_at TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_image_paths_content_hash
  ON image_paths(content_hash);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  job_type TEXT NOT NULL,
  status TEXT NOT NULL,
  requested_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  summary_json TEXT,
  error_text TEXT
);

CREATE TABLE IF NOT EXISTS system_state (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    parent_id   INTEGER REFERENCES categories(id),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    UNIQUE(parent_id, name)
);

CREATE TABLE IF NOT EXISTS image_tags (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash  TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
    tag_id        INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    category_id   INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at    TEXT NOT NULL,
    UNIQUE(content_hash, tag_id),
    UNIQUE(content_hash, category_id),
    CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_image_tags_content_hash ON image_tags(content_hash);
CREATE INDEX IF NOT EXISTS idx_image_tags_tag_id ON image_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_image_tags_category_id ON image_tags(category_id);
