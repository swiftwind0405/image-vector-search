from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from image_vector_search.repositories.sqlite import MetadataRepository


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_legacy_db(path: Path) -> None:
    """Create a DB that matches the schema before category removal."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE images (
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
          embedding_status TEXT NOT NULL DEFAULT 'embedded',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL
        );
        CREATE TABLE categories (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          parent_id INTEGER REFERENCES categories(id),
          sort_order INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL,
          UNIQUE(parent_id, name)
        );
        CREATE TABLE image_tags (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          content_hash TEXT NOT NULL REFERENCES images(content_hash) ON DELETE CASCADE,
          tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
          category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
          created_at TEXT NOT NULL,
          UNIQUE(content_hash, tag_id),
          UNIQUE(content_hash, category_id),
          CHECK((tag_id IS NOT NULL) != (category_id IS NOT NULL))
        );
        CREATE INDEX idx_image_tags_category_id ON image_tags(category_id);
        """
    )
    now = _iso_now()
    conn.execute(
        "INSERT INTO images VALUES ('h1','/img/1.jpg',1,0,'image/jpeg',1,1,1,?, 'jina','v1','1','embedded',?,?)",
        (now, now, now),
    )
    conn.execute("INSERT INTO tags (name, created_at) VALUES ('red', ?)", (now,))
    conn.execute(
        "INSERT INTO categories (name, parent_id, created_at) VALUES ('Nature', NULL, ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES ('h1', 1, NULL, ?)",
        (now,),
    )
    conn.execute(
        "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES ('h1', NULL, 1, ?)",
        (now,),
    )
    conn.commit()
    conn.close()


def test_drop_category_schema_migrates_legacy_db(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.sqlite"
    _build_legacy_db(db_path)

    MetadataRepository(db_path)

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "categories" not in tables

        columns = {row[1] for row in conn.execute("PRAGMA table_info(image_tags)")}
        assert "category_id" not in columns
        assert columns >= {"content_hash", "tag_id", "created_at"}

        rows = conn.execute("SELECT content_hash, tag_id FROM image_tags").fetchall()
        assert rows == [("h1", 1)]
    finally:
        conn.close()


def test_drop_category_schema_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.sqlite"
    MetadataRepository(db_path)
    MetadataRepository(db_path)

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "categories" not in tables
    finally:
        conn.close()
