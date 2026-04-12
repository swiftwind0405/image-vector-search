import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from image_vector_search.domain.models import (
    Album,
    AlbumRule,
    Category,
    CategoryNode,
    ImagePathRecord,
    PaginatedAlbumImages,
    PaginatedImages,
    ImageRecord,
    ImageRecordWithLabels,
    JobRecord,
    StatusAggregates,
    Tag,
)

EMBEDDING_PROVIDER_STATE_KEY = "config.embedding_provider"
JINA_API_KEY_STATE_KEY = "config.jina_api_key"
GOOGLE_API_KEY_STATE_KEY = "config.google_api_key"


def choose_canonical_path(existing: str | None, active_paths: list[str]) -> str | None:
    if existing and existing in active_paths:
        return existing
    if not active_paths:
        return None
    return sorted(active_paths)[0]


def _escape_like_pattern(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


class MetadataRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema_sql)
            self._ensure_embedding_status_column(connection)
            self._ensure_album_schema(connection)

    def upsert_image(self, image: ImageRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO images (
                    content_hash, canonical_path, file_size, mtime, mime_type, width, height,
                    is_active, last_seen_at, embedding_provider, embedding_model, embedding_version,
                    embedding_status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(content_hash) DO UPDATE SET
                    canonical_path = excluded.canonical_path,
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    mime_type = excluded.mime_type,
                    width = excluded.width,
                    height = excluded.height,
                    is_active = excluded.is_active,
                    last_seen_at = excluded.last_seen_at,
                    embedding_provider = excluded.embedding_provider,
                    embedding_model = excluded.embedding_model,
                    embedding_version = excluded.embedding_version,
                    embedding_status = excluded.embedding_status,
                    updated_at = excluded.updated_at
                """,
                (
                    image.content_hash,
                    image.canonical_path,
                    image.file_size,
                    image.mtime,
                    image.mime_type,
                    image.width,
                    image.height,
                    1 if image.is_active else 0,
                    _to_iso(image.last_seen_at),
                    image.embedding_provider,
                    image.embedding_model,
                    image.embedding_version,
                    image.embedding_status,
                    _to_iso(image.created_at),
                    _to_iso(image.updated_at),
                ),
            )

    def get_image(self, content_hash: str) -> ImageRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM images WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_image(row)

    def get_active_image_by_canonical_path(self, canonical_path: str) -> ImageRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM images
                WHERE canonical_path = ? AND is_active = 1
                """,
                (canonical_path,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_image(row)

    def list_active_images(
        self,
        folder: str | None = None,
        images_root: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
        limit: int | None = None,
        cursor: str | None = None,
        embedding_status: str | None = None,
    ) -> list[ImageRecord]:
        page = self._list_images_page(
            active_only=True,
            folder=folder,
            images_root=images_root,
            embedding_status=embedding_status,
            tag_id=tag_id,
            category_id=category_id,
            include_descendants=include_descendants,
            limit=limit,
            cursor=cursor,
        )
        return page.items

    def list_active_images_with_labels(
        self,
        folder: str | None = None,
        images_root: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
        limit: int | None = None,
        cursor: str | None = None,
        embedding_status: str | None = None,
    ) -> PaginatedImages:
        return self._list_images_page(
            active_only=True,
            folder=folder,
            images_root=images_root,
            embedding_status=embedding_status,
            tag_id=tag_id,
            category_id=category_id,
            include_descendants=include_descendants,
            limit=limit,
            cursor=cursor,
        )

    def list_all_images_with_labels(
        self,
        folder: str | None = None,
        images_root: str | None = None,
        embedding_status: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedImages:
        return self._list_images_page(
            active_only=False,
            folder=folder,
            images_root=images_root,
            embedding_status=embedding_status,
            tag_id=tag_id,
            category_id=category_id,
            include_descendants=include_descendants,
            limit=limit,
            cursor=cursor,
        )

    def list_inactive_images(self) -> list[ImageRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM images WHERE is_active = 0 ORDER BY canonical_path ASC"
            ).fetchall()
        return [_row_to_image(row) for row in rows]

    def list_folders(self, images_root: str) -> list[str]:
        root = images_root.rstrip("/") + "/"
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT canonical_path FROM images WHERE is_active = 1"
            ).fetchall()
        folders: set[str] = set()
        for row in rows:
            path = str(row["canonical_path"])
            if path.startswith(root):
                relative = path[len(root):]
                # Get the parent directory portion (everything except the filename)
                parts = relative.rsplit("/", 1)
                if len(parts) == 2:
                    folders.add(parts[0])
        return sorted(folders)

    def list_images_in_folder(
        self,
        path: str,
        images_root: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ImageRecord]:
        normalized_path = path.strip("/")
        base_root = images_root.rstrip("/")
        prefix_no_wild = (
            f"{base_root}/"
            if not normalized_path
            else f"{base_root}/{normalized_path}/"
        )
        like_prefix = _escape_like_pattern(prefix_no_wild) + "%"
        params: dict[str, object] = {
            "prefix": like_prefix,
            "prefix_no_wild": prefix_no_wild,
            "cursor": cursor,
        }
        sql = """
            SELECT *
            FROM images
            WHERE is_active = 1
              AND canonical_path LIKE :prefix ESCAPE '\\'
              AND instr(substr(canonical_path, length(:prefix_no_wild) + 1), '/') = 0
              AND (:cursor IS NULL OR canonical_path > :cursor)
            ORDER BY canonical_path ASC
        """
        if limit is not None:
            sql += "\n LIMIT :limit"
            params["limit"] = limit
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_row_to_image(row) for row in rows]

    def get_image_path(self, path: str) -> ImagePathRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM image_paths WHERE path = ?",
                (path,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_image_path(row)

    def upsert_image_path(self, image_path: ImagePathRecord) -> None:
        seen_at_text = _to_iso(image_path.last_seen_at)
        with self.connect() as connection:
            previous_row = connection.execute(
                "SELECT content_hash FROM image_paths WHERE path = ?",
                (image_path.path,),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO image_paths (
                    content_hash, path, file_size, mtime, is_active, last_seen_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    file_size = excluded.file_size,
                    mtime = excluded.mtime,
                    is_active = excluded.is_active,
                    last_seen_at = excluded.last_seen_at,
                    updated_at = excluded.updated_at
                """,
                (
                    image_path.content_hash,
                    image_path.path,
                    image_path.file_size,
                    image_path.mtime,
                    1 if image_path.is_active else 0,
                    seen_at_text,
                    _to_iso(image_path.created_at),
                    _to_iso(image_path.updated_at),
                ),
            )
            hashes_to_refresh = {image_path.content_hash}
            if (
                previous_row is not None
                and str(previous_row["content_hash"]) != image_path.content_hash
            ):
                hashes_to_refresh.add(str(previous_row["content_hash"]))
            refresh_seen_at = seen_at_text or _to_iso(image_path.updated_at)
            for content_hash in hashes_to_refresh:
                self._refresh_image_activity(connection, content_hash, refresh_seen_at)

    def list_active_paths(self, content_hash: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT path
                FROM image_paths
                WHERE content_hash = ? AND is_active = 1
                ORDER BY path ASC
                """,
                (content_hash,),
            ).fetchall()
        return [str(row["path"]) for row in rows]

    def mark_unseen_paths_inactive(
        self, seen_paths: list[str], seen_at: datetime
    ) -> int:
        seen_at_text = _to_iso(seen_at)
        with self.connect() as connection:
            if seen_paths:
                placeholders = ", ".join("?" for _ in seen_paths)
                unseen_where = f"is_active = 1 AND path NOT IN ({placeholders})"
                unseen_params: tuple[str, ...] = tuple(seen_paths)
            else:
                unseen_where = "is_active = 1"
                unseen_params = ()

            hashes_to_refresh = [
                row["content_hash"]
                for row in connection.execute(
                    f"SELECT DISTINCT content_hash FROM image_paths WHERE {unseen_where}",
                    unseen_params,
                ).fetchall()
            ]

            result = connection.execute(
                f"""
                UPDATE image_paths
                SET is_active = 0, updated_at = ?
                WHERE {unseen_where}
                """,
                (seen_at_text, *unseen_params),
            )

            for content_hash in hashes_to_refresh:
                self._refresh_image_activity(connection, content_hash, seen_at_text)

            return result.rowcount

    def read_status_aggregates(self) -> StatusAggregates:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total_images,
                    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_images
                FROM images
                """
            ).fetchone()
        total_images = int(row["total_images"]) if row else 0
        active_images = int(row["active_images"] or 0) if row else 0
        return StatusAggregates(
            total_images=total_images,
            active_images=active_images,
            inactive_images=total_images - active_images,
        )

    def purge_images(self, content_hashes: list[str]) -> int:
        if not content_hashes:
            return 0

        placeholders = ", ".join("?" for _ in content_hashes)
        with self.connect() as connection:
            connection.execute(
                f"DELETE FROM image_tags WHERE content_hash IN ({placeholders})",
                content_hashes,
            )
            connection.execute(
                f"DELETE FROM image_paths WHERE content_hash IN ({placeholders})",
                content_hashes,
            )
            result = connection.execute(
                f"DELETE FROM images WHERE content_hash IN ({placeholders})",
                content_hashes,
            )
            return result.rowcount

    def create_job(self, job: JobRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    id, job_type, status, requested_at, started_at, finished_at, summary_json, error_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    job_type = excluded.job_type,
                    status = excluded.status,
                    requested_at = excluded.requested_at,
                    started_at = excluded.started_at,
                    finished_at = excluded.finished_at,
                    summary_json = excluded.summary_json,
                    error_text = excluded.error_text
                """,
                (
                    job.id,
                    job.job_type,
                    job.status,
                    _to_iso(job.requested_at),
                    _to_iso(job.started_at),
                    _to_iso(job.finished_at),
                    job.summary_json,
                    job.error_text,
                ),
            )

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        summary_json: str | None = None,
        error_text: str | None = None,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET
                    status = ?,
                    started_at = COALESCE(?, started_at),
                    finished_at = COALESCE(?, finished_at),
                    summary_json = COALESCE(?, summary_json),
                    error_text = COALESCE(?, error_text)
                WHERE id = ?
                """,
                (
                    status,
                    _to_iso(started_at),
                    _to_iso(finished_at),
                    summary_json,
                    error_text,
                    job_id,
                ),
            )

    def get_job(self, job_id: str) -> JobRecord | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_job(row)

    def list_recent_jobs(self, limit: int = 20) -> list[JobRecord]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM jobs
                ORDER BY requested_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_job(row) for row in rows]

    def create_tag(self, name: str) -> Tag:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO tags (name, created_at) VALUES (?, ?)",
                (name, now),
            )
            return Tag(id=cursor.lastrowid, name=name, created_at=_from_iso(now))

    def create_album(
        self,
        name: str,
        album_type: str,
        description: str | None = None,
        rule_logic: str | None = None,
    ) -> Album:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO albums (name, type, description, rule_logic, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name, album_type, description or "", rule_logic, now, now),
            )
        album = self.get_album(int(cursor.lastrowid))
        if album is None:
            raise RuntimeError("Failed to read newly created album")
        return album

    def list_albums(self) -> list[Album]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT a.*
                FROM albums a
                ORDER BY a.name
                """
            ).fetchall()
        albums = [self._album_from_row(row) for row in rows]
        for album in albums:
            album.source_paths = self.get_album_source_paths(album.id)
            if album.type == "manual":
                album.image_count = self._count_manual_album_images(album.id)
                album.cover_image = self._get_manual_album_cover(album.id)
            else:
                page = self.list_smart_album_images(album.id, limit=1, cursor=None)
                album.image_count = self.count_smart_album_images(album.id)
                album.cover_image = page.items[0] if page.items else None
        return albums

    def get_album(self, album_id: int) -> Album | None:
        row = self._get_album_row(album_id)
        if row is None:
            return None
        album = self._album_from_row(row)
        album.source_paths = self.get_album_source_paths(album.id)
        if album.type == "manual":
            album.image_count = self._count_manual_album_images(album.id)
            album.cover_image = self._get_manual_album_cover(album.id)
        else:
            page = self.list_smart_album_images(album.id, limit=1, cursor=None)
            album.image_count = self.count_smart_album_images(album.id)
            album.cover_image = page.items[0] if page.items else None
        return album

    def update_album(
        self,
        album_id: int,
        name: str,
        description: str | None = None,
    ) -> Album | None:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE albums
                SET name = ?, description = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, description or "", now, album_id),
            )
        return self.get_album(album_id)

    def delete_album(self, album_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM albums WHERE id = ?", (album_id,))

    def add_images_to_album(self, album_id: int, content_hashes: list[str]) -> int:
        if not content_hashes:
            return 0
        added_at = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            current_max_sort_order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) AS max_sort_order FROM album_images WHERE album_id = ?",
                (album_id,),
            ).fetchone()["max_sort_order"]
            rows = [
                (album_id, content_hash, int(current_max_sort_order) + index + 1, added_at)
                for index, content_hash in enumerate(content_hashes)
            ]
            cursor = conn.executemany(
                """
                INSERT OR IGNORE INTO album_images (album_id, content_hash, sort_order, added_at)
                VALUES (?, ?, ?, ?)
                """,
                rows,
            )
            return cursor.rowcount

    def remove_images_from_album(self, album_id: int, content_hashes: list[str]) -> int:
        if not content_hashes:
            return 0
        placeholders = ",".join("?" * len(content_hashes))
        with self.connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM album_images WHERE album_id = ? AND content_hash IN ({placeholders})",
                [album_id, *content_hashes],
            )
            return cursor.rowcount

    def list_album_images(
        self,
        album_id: int,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedAlbumImages:
        params: list[object] = [album_id]
        cursor_clause = ""
        if cursor is not None:
            sort_order, album_image_id = _parse_album_images_cursor(cursor)
            cursor_clause = """
                AND (
                    ai.sort_order > ?
                    OR (ai.sort_order = ? AND ai.id > ?)
                )
            """
            params.extend([sort_order, sort_order, album_image_id])
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit + 1)
        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT images.*, ai.sort_order AS album_sort_order, ai.id AS album_image_id
                FROM images
                JOIN album_images ai ON ai.content_hash = images.content_hash
                WHERE ai.album_id = ?
                  AND images.is_active = 1
                  {cursor_clause}
                ORDER BY ai.sort_order ASC, ai.id ASC, images.canonical_path ASC
                {limit_clause}
                """,
                params,
            ).fetchall()
        has_more = limit is not None and len(rows) > limit
        page_rows = rows[:limit] if has_more and limit is not None else rows
        images = [_row_to_image(row) for row in page_rows]
        if not images:
            return PaginatedAlbumImages(items=[], next_cursor=None)
        hashes = [img.content_hash for img in images]
        tags_map = self.get_tags_for_images(hashes)
        cats_map = self.get_categories_for_images(hashes)
        items = [
            ImageRecordWithLabels(
                **img.model_dump(),
                tags=tags_map.get(img.content_hash, []),
                categories=cats_map.get(img.content_hash, []),
            )
            for img in images
        ]
        next_cursor = None
        if has_more:
            last_row = page_rows[-1]
            next_cursor = f"{int(last_row['album_sort_order'])}:{int(last_row['album_image_id'])}"
        return PaginatedAlbumImages(items=items, next_cursor=next_cursor)

    def set_album_rules(self, album_id: int, rules: list[dict[str, object]]) -> None:
        tag_ids = [int(rule["tag_id"]) for rule in rules]
        if len(tag_ids) != len(set(tag_ids)):
            raise ValueError("Duplicate tag_id in album rules")
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            conn.execute("DELETE FROM album_rules WHERE album_id = ?", (album_id,))
            if rules:
                conn.executemany(
                    """
                    INSERT INTO album_rules (album_id, tag_id, match_mode, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    [
                        (album_id, int(rule["tag_id"]), str(rule["match_mode"]), now)
                        for rule in rules
                    ],
                )

    def get_album_rules(self, album_id: int) -> list[AlbumRule]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT ar.id, ar.album_id, ar.tag_id, ar.match_mode, ar.created_at, t.name AS tag_name
                FROM album_rules ar
                LEFT JOIN tags t ON t.id = ar.tag_id
                WHERE ar.album_id = ?
                ORDER BY ar.id
                """,
                (album_id,),
            ).fetchall()
        return [
            AlbumRule(
                id=int(row["id"]),
                album_id=int(row["album_id"]),
                tag_id=int(row["tag_id"]),
                match_mode=row["match_mode"],
                created_at=_from_iso(row["created_at"]) or datetime.min,
                tag_name=row["tag_name"],
            )
            for row in rows
        ]

    def set_album_source_paths(self, album_id: int, paths: list[str]) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM album_source_paths WHERE album_id = ?", (album_id,))
            if paths:
                now = _to_iso(datetime.now(timezone.utc))
                conn.executemany(
                    """
                    INSERT INTO album_source_paths (album_id, path, created_at)
                    VALUES (?, ?, ?)
                    """,
                    [(album_id, path, now) for path in paths],
                )

    def get_album_source_paths(self, album_id: int) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT path
                FROM album_source_paths
                WHERE album_id = ?
                ORDER BY id
                """,
                (album_id,),
            ).fetchall()
        return [str(row["path"]) for row in rows]

    def list_smart_album_images(
        self,
        album_id: int,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedAlbumImages:
        sql, params, has_include_rules = self._build_smart_album_query(
            album_id=album_id,
            select_count=False,
            limit=limit,
            cursor=cursor,
        )
        if not has_include_rules:
            return PaginatedAlbumImages(items=[], next_cursor=None)
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._build_album_images_page(rows, limit)

    def count_smart_album_images(self, album_id: int) -> int:
        sql, params, has_include_rules = self._build_smart_album_query(
            album_id=album_id,
            select_count=True,
            limit=None,
            cursor=None,
        )
        if not has_include_rules:
            return 0
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return int(row["count"]) if row is not None else 0

    def list_tags(self) -> list[Tag]:
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT t.id, t.name, t.created_at, COUNT(it.content_hash) AS image_count
                FROM tags t
                LEFT JOIN image_tags it ON t.id = it.tag_id
                GROUP BY t.id, t.name, t.created_at
                ORDER BY t.name
            """).fetchall()
            return [
                Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"]), image_count=r["image_count"])
                for r in rows
            ]

    def rename_tag(self, tag_id: int, new_name: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (new_name, tag_id))

    def delete_tag(self, tag_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))

    def create_category(self, name: str, parent_id: int | None = None) -> Category:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO categories (name, parent_id, sort_order, created_at) VALUES (?, ?, 0, ?)",
                (name, parent_id, now),
            )
            return Category(
                id=cursor.lastrowid, name=name, parent_id=parent_id,
                sort_order=0, created_at=_from_iso(now),
            )

    def list_categories(self, parent_id: int | None = None) -> list[Category]:
        with self.connect() as conn:
            if parent_id is None:
                rows = conn.execute(
                    "SELECT id, name, parent_id, sort_order, created_at FROM categories WHERE parent_id IS NULL ORDER BY sort_order, name"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, name, parent_id, sort_order, created_at FROM categories WHERE parent_id = ? ORDER BY sort_order, name",
                    (parent_id,),
                ).fetchall()
            return [self._row_to_category(r) for r in rows]

    def get_category_tree(self) -> list[CategoryNode]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, name, parent_id, sort_order, created_at FROM categories ORDER BY sort_order, name"
            ).fetchall()
            count_rows = conn.execute(
                "SELECT category_id, COUNT(DISTINCT content_hash) AS image_count FROM image_tags WHERE category_id IS NOT NULL GROUP BY category_id"
            ).fetchall()
        counts = {r["category_id"]: r["image_count"] for r in count_rows}
        nodes: dict[int, CategoryNode] = {}
        for r in rows:
            nodes[r["id"]] = CategoryNode(
                id=r["id"], name=r["name"], parent_id=r["parent_id"],
                sort_order=r["sort_order"], created_at=_from_iso(r["created_at"]),
                image_count=counts.get(r["id"], 0),
            )
        roots: list[CategoryNode] = []
        for node in nodes.values():
            if node.parent_id is not None and node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    def rename_category(self, category_id: int, new_name: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, category_id))

    def move_category(self, category_id: int, new_parent_id: int | None) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE categories SET parent_id = ? WHERE id = ?", (new_parent_id, category_id))

    def delete_category(self, category_id: int) -> None:
        with self.connect() as conn:
            rows = conn.execute("""
                WITH RECURSIVE descendants(id) AS (
                    SELECT id FROM categories WHERE id = ?
                    UNION ALL
                    SELECT c.id FROM categories c JOIN descendants d ON c.parent_id = d.id
                )
                SELECT id FROM descendants
            """, (category_id,)).fetchall()
            ids = [r["id"] for r in rows]
            if not ids:
                return
            placeholders = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM image_tags WHERE category_id IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM categories WHERE id IN ({placeholders})", ids)

    def bulk_delete_tags(self, tag_ids: list[int]) -> int:
        if not tag_ids:
            return 0
        with self.connect() as conn:
            placeholders = ",".join("?" * len(tag_ids))
            cursor = conn.execute(
                f"DELETE FROM tags WHERE id IN ({placeholders})", tag_ids,
            )
            return cursor.rowcount

    def bulk_delete_categories(self, category_ids: list[int]) -> int:
        if not category_ids:
            return 0
        with self.connect() as conn:
            all_ids: set[int] = set()
            for cid in category_ids:
                rows = conn.execute("""
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c JOIN descendants d ON c.parent_id = d.id
                    )
                    SELECT id FROM descendants
                """, (cid,)).fetchall()
                all_ids.update(r["id"] for r in rows)
            if not all_ids:
                return 0
            ids = list(all_ids)
            placeholders = ",".join("?" * len(ids))
            conn.execute(f"DELETE FROM image_tags WHERE category_id IN ({placeholders})", ids)
            cursor = conn.execute(f"DELETE FROM categories WHERE id IN ({placeholders})", ids)
            return cursor.rowcount

    def add_tag_to_image(self, content_hash: str, tag_id: int) -> None:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
                (content_hash, tag_id, now),
            )

    def remove_tag_from_image(self, content_hash: str, tag_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM image_tags WHERE content_hash = ? AND tag_id = ?",
                (content_hash, tag_id),
            )

    def add_image_to_category(self, content_hash: str, category_id: int) -> None:
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
                (content_hash, category_id, now),
            )

    def remove_image_from_category(self, content_hash: str, category_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM image_tags WHERE content_hash = ? AND category_id = ?",
                (content_hash, category_id),
            )

    def get_image_tags(self, content_hash: str) -> list[Tag]:
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT t.id, t.name, t.created_at
                FROM tags t JOIN image_tags it ON t.id = it.tag_id
                WHERE it.content_hash = ?
                ORDER BY t.name
            """, (content_hash,)).fetchall()
            return [Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"])) for r in rows]

    def get_image_categories(self, content_hash: str) -> list[Category]:
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT c.id, c.name, c.parent_id, c.sort_order, c.created_at
                FROM categories c JOIN image_tags it ON c.id = it.category_id
                WHERE it.content_hash = ?
                ORDER BY c.name
            """, (content_hash,)).fetchall()
            return [self._row_to_category(r) for r in rows]

    def get_tags_for_images(self, content_hashes: list[str]) -> dict[str, list[Tag]]:
        if not content_hashes:
            return {}
        with self.connect() as conn:
            placeholders = ",".join("?" * len(content_hashes))
            rows = conn.execute(f"""
                SELECT it.content_hash, t.id, t.name, t.created_at
                FROM tags t JOIN image_tags it ON t.id = it.tag_id
                WHERE it.content_hash IN ({placeholders})
                ORDER BY t.name
            """, content_hashes).fetchall()
        result: dict[str, list[Tag]] = {}
        for r in rows:
            tag = Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"]))
            result.setdefault(r["content_hash"], []).append(tag)
        return result

    def get_categories_for_images(self, content_hashes: list[str]) -> dict[str, list[Category]]:
        if not content_hashes:
            return {}
        with self.connect() as conn:
            placeholders = ",".join("?" * len(content_hashes))
            rows = conn.execute(f"""
                SELECT it.content_hash, c.id, c.name, c.parent_id, c.sort_order, c.created_at
                FROM categories c JOIN image_tags it ON c.id = it.category_id
                WHERE it.content_hash IN ({placeholders})
                ORDER BY c.name
            """, content_hashes).fetchall()
        result: dict[str, list[Category]] = {}
        for r in rows:
            cat = self._row_to_category(r)
            result.setdefault(r["content_hash"], []).append(cat)
        return result

    def filter_by_tags(self, tag_ids: list[int]) -> set[str]:
        if not tag_ids:
            return set()
        with self.connect() as conn:
            placeholders = ",".join("?" * len(tag_ids))
            rows = conn.execute(f"""
                SELECT content_hash
                FROM image_tags
                WHERE tag_id IN ({placeholders})
                GROUP BY content_hash
                HAVING COUNT(DISTINCT tag_id) = ?
            """, [*tag_ids, len(tag_ids)]).fetchall()
            return {r["content_hash"] for r in rows}

    def filter_by_category(self, category_id: int, include_subcategories: bool = True) -> set[str]:
        with self.connect() as conn:
            if include_subcategories:
                rows = conn.execute("""
                    WITH RECURSIVE descendants(id) AS (
                        SELECT id FROM categories WHERE id = ?
                        UNION ALL
                        SELECT c.id FROM categories c JOIN descendants d ON c.parent_id = d.id
                    )
                    SELECT DISTINCT it.content_hash
                    FROM image_tags it
                    WHERE it.category_id IN (SELECT id FROM descendants)
                """, (category_id,)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT DISTINCT content_hash FROM image_tags WHERE category_id = ?",
                    (category_id,),
                ).fetchall()
            return {r["content_hash"] for r in rows}

    def bulk_add_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if not content_hashes:
            return 0
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            cursor = conn.executemany(
                "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
                [(h, tag_id, now) for h in content_hashes],
            )
            return cursor.rowcount

    def bulk_remove_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if not content_hashes:
            return 0
        placeholders = ",".join("?" * len(content_hashes))
        with self.connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND tag_id = ?",
                [*content_hashes, tag_id],
            )
            return cursor.rowcount

    def bulk_add_category(self, content_hashes: list[str], category_id: int) -> int:
        if not content_hashes:
            return 0
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            cursor = conn.executemany(
                "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
                [(h, category_id, now) for h in content_hashes],
            )
            return cursor.rowcount

    def bulk_remove_category(self, content_hashes: list[str], category_id: int) -> int:
        if not content_hashes:
            return 0
        placeholders = ",".join("?" * len(content_hashes))
        with self.connect() as conn:
            cursor = conn.execute(
                f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND category_id = ?",
                [*content_hashes, category_id],
            )
            return cursor.rowcount

    def bulk_folder_add_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
                (prefix + "%",),
            ).fetchall()
            hashes = [str(r["content_hash"]) for r in rows]
            if not hashes:
                return 0
            cursor = conn.executemany(
                "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, ?, NULL, ?)",
                [(h, tag_id, now) for h in hashes],
            )
            return cursor.rowcount

    def bulk_folder_remove_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
                (prefix + "%",),
            ).fetchall()
            hashes = [str(r["content_hash"]) for r in rows]
            if not hashes:
                return 0
            placeholders = ",".join("?" * len(hashes))
            cursor = conn.execute(
                f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND tag_id = ?",
                [*hashes, tag_id],
            )
            return cursor.rowcount

    def bulk_folder_add_category(self, folder: str, category_id: int, images_root: str) -> int:
        prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
        now = _to_iso(datetime.now(timezone.utc))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
                (prefix + "%",),
            ).fetchall()
            hashes = [str(r["content_hash"]) for r in rows]
            if not hashes:
                return 0
            cursor = conn.executemany(
                "INSERT OR IGNORE INTO image_tags (content_hash, tag_id, category_id, created_at) VALUES (?, NULL, ?, ?)",
                [(h, category_id, now) for h in hashes],
            )
            return cursor.rowcount

    def bulk_folder_remove_category(self, folder: str, category_id: int, images_root: str) -> int:
        prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT content_hash FROM images WHERE is_active = 1 AND canonical_path LIKE ?",
                (prefix + "%",),
            ).fetchall()
            hashes = [str(r["content_hash"]) for r in rows]
            if not hashes:
                return 0
            placeholders = ",".join("?" * len(hashes))
            cursor = conn.execute(
                f"DELETE FROM image_tags WHERE content_hash IN ({placeholders}) AND category_id = ?",
                [*hashes, category_id],
            )
            return cursor.rowcount

    def _row_to_category(self, row) -> Category:
        return Category(
            id=row["id"], name=row["name"], parent_id=row["parent_id"],
            sort_order=row["sort_order"], created_at=_from_iso(row["created_at"]),
        )

    def _album_from_row(self, row: sqlite3.Row) -> Album:
        return Album(
            id=int(row["id"]),
            name=row["name"],
            type=row["type"],
            description=row["description"] or "",
            rule_logic=row["rule_logic"],
            source_paths=[],
            image_count=None,
            cover_image=None,
            created_at=_from_iso(row["created_at"]) or datetime.min,
            updated_at=_from_iso(row["updated_at"]) or datetime.min,
        )

    def _get_album_row(self, album_id: int) -> sqlite3.Row | None:
        with self.connect() as conn:
            return conn.execute(
                """
                SELECT a.*
                FROM albums a
                WHERE a.id = ?
                """,
                (album_id,),
            ).fetchone()

    def _count_manual_album_images(self, album_id: int) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM album_images WHERE album_id = ?",
                (album_id,),
            ).fetchone()
        return int(row["count"]) if row is not None else 0

    def _get_manual_album_cover(self, album_id: int) -> ImageRecordWithLabels | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT images.*
                FROM images
                JOIN album_images ai ON ai.content_hash = images.content_hash
                WHERE ai.album_id = ?
                  AND images.is_active = 1
                ORDER BY ai.sort_order ASC, ai.id ASC, images.canonical_path ASC
                LIMIT 1
                """,
                (album_id,),
            ).fetchone()
        if row is None:
            return None
        return self._build_image_with_labels(_row_to_image(row))

    def _build_image_with_labels(self, image: ImageRecord) -> ImageRecordWithLabels:
        tags = self.get_tags_for_images([image.content_hash]).get(image.content_hash, [])
        categories = self.get_categories_for_images([image.content_hash]).get(image.content_hash, [])
        return ImageRecordWithLabels(
            **image.model_dump(),
            tags=tags,
            categories=categories,
        )

    def _build_album_images_page(
        self,
        rows: list[sqlite3.Row],
        limit: int | None,
    ) -> PaginatedAlbumImages:
        has_more = limit is not None and len(rows) > limit
        page_rows = rows[:limit] if has_more and limit is not None else rows
        images = [_row_to_image(row) for row in page_rows]
        if not images:
            return PaginatedAlbumImages(items=[], next_cursor=None)
        hashes = [img.content_hash for img in images]
        tags_map = self.get_tags_for_images(hashes)
        cats_map = self.get_categories_for_images(hashes)
        items = [
            ImageRecordWithLabels(
                **img.model_dump(),
                tags=tags_map.get(img.content_hash, []),
                categories=cats_map.get(img.content_hash, []),
            )
            for img in images
        ]
        next_cursor = items[-1].canonical_path if has_more else None
        return PaginatedAlbumImages(items=items, next_cursor=next_cursor)

    def _build_smart_album_query(
        self,
        *,
        album_id: int,
        select_count: bool,
        limit: int | None,
        cursor: str | None,
    ) -> tuple[str, list[object], bool]:
        album_row = self._get_album_row(album_id)
        if album_row is None:
            return ("SELECT 0 AS count" if select_count else "SELECT * FROM images WHERE 1 = 0", [], False)
        album_type = album_row["type"]
        rule_logic = album_row["rule_logic"]
        if album_type != "smart":
            return ("SELECT 0 AS count" if select_count else "SELECT * FROM images WHERE 1 = 0", [], False)

        rules = self.get_album_rules(album_id)
        include_tag_ids = [rule.tag_id for rule in rules if rule.match_mode == "include"]
        exclude_tag_ids = [rule.tag_id for rule in rules if rule.match_mode == "exclude"]
        source_paths = self.get_album_source_paths(album_id)

        if not include_tag_ids:
            return ("SELECT 0 AS count" if select_count else "SELECT * FROM images WHERE 1 = 0", [], False)

        params: list[object] = []
        path_clause = ""
        if source_paths:
            path_parts: list[str] = []
            for source_path in source_paths:
                normalized = source_path.strip("/")
                path_parts.append("images.canonical_path LIKE ?")
                params.append(f"%/{normalized}/%")
            path_clause = " AND (" + " OR ".join(path_parts) + ")"

        exclude_clause = ""
        if exclude_tag_ids:
            placeholders = ",".join("?" * len(exclude_tag_ids))
            exclude_clause = (
                " AND images.content_hash NOT IN ("
                "SELECT content_hash FROM image_tags WHERE tag_id IN (" + placeholders + ")"
                ")"
            )
            params.extend(exclude_tag_ids)

        if rule_logic == "and":
            include_placeholders = ",".join("?" * len(include_tag_ids))
            select_sql = "COUNT(*) AS count" if select_count else "images.*"
            sql = f"""
                SELECT {select_sql}
                FROM images
                JOIN image_tags it ON it.content_hash = images.content_hash
                WHERE images.is_active = 1
                  AND it.tag_id IN ({include_placeholders})
                  {path_clause}
                  {exclude_clause}
            """
            params = [*include_tag_ids, *params]
            if cursor is not None and not select_count:
                sql += " AND images.canonical_path > ?"
                params.append(cursor)
            sql += """
                GROUP BY images.content_hash
                HAVING COUNT(DISTINCT it.tag_id) = ?
            """
            params.append(len(include_tag_ids))
            if select_count:
                sql = f"SELECT COUNT(*) AS count FROM ({sql}) matched_images"
            else:
                sql += " ORDER BY images.canonical_path"
                if limit is not None:
                    sql += " LIMIT ?"
                    params.append(limit + 1)
            return (sql, params, True)

        include_placeholders = ",".join("?" * len(include_tag_ids))
        select_sql = "COUNT(DISTINCT images.content_hash) AS count" if select_count else "DISTINCT images.*"
        sql = f"""
            SELECT {select_sql}
            FROM images
            JOIN image_tags it ON it.content_hash = images.content_hash
            WHERE images.is_active = 1
              AND it.tag_id IN ({include_placeholders})
              {path_clause}
              {exclude_clause}
        """
        params = [*include_tag_ids, *params]
        if cursor is not None and not select_count:
            sql += " AND images.canonical_path > ?"
            params.append(cursor)
        if not select_count:
            sql += " ORDER BY images.canonical_path"
            if limit is not None:
                sql += " LIMIT ?"
                params.append(limit + 1)
        return (sql, params, True)

    def _list_images_page(
        self,
        *,
        active_only: bool,
        folder: str | None,
        images_root: str | None,
        embedding_status: str | None,
        tag_id: int | None,
        category_id: int | None,
        include_descendants: bool,
        limit: int | None,
        cursor: str | None,
    ) -> PaginatedImages:
        sql, params = self._build_list_images_query(
            active_only=active_only,
            folder=folder,
            images_root=images_root,
            embedding_status=embedding_status,
            tag_id=tag_id,
            category_id=category_id,
            include_descendants=include_descendants,
            limit=limit,
            cursor=cursor,
        )
        with self.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        has_more = limit is not None and len(rows) > limit
        page_rows = rows[:limit] if has_more and limit is not None else rows
        images = [_row_to_image(row) for row in page_rows]
        if not images:
            return PaginatedImages(items=[], next_cursor=None)
        hashes = [img.content_hash for img in images]
        tags_map = self.get_tags_for_images(hashes)
        cats_map = self.get_categories_for_images(hashes)
        items = [
            ImageRecordWithLabels(
                **img.model_dump(),
                tags=tags_map.get(img.content_hash, []),
                categories=cats_map.get(img.content_hash, []),
            )
            for img in images
        ]
        next_cursor = items[-1].canonical_path if has_more else None
        return PaginatedImages(items=items, next_cursor=next_cursor)

    def _build_list_images_query(
        self,
        *,
        active_only: bool,
        folder: str | None,
        images_root: str | None,
        embedding_status: str | None,
        tag_id: int | None,
        category_id: int | None,
        include_descendants: bool,
        limit: int | None,
        cursor: str | None,
    ) -> tuple[str, list[object]]:
        ctes: list[str] = []
        params: list[object] = []
        where: list[str] = []

        if active_only:
            where.append("images.is_active = 1")
        if folder is not None and images_root is not None:
            prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
            where.append("images.canonical_path LIKE ?")
            params.append(prefix + "%")
        if embedding_status is not None:
            where.append("images.embedding_status = ?")
            params.append(embedding_status)
        if tag_id is not None:
            where.append(
                """
                EXISTS (
                    SELECT 1
                    FROM image_tags it
                    WHERE it.content_hash = images.content_hash
                      AND it.tag_id = ?
                )
                """.strip()
            )
            params.append(tag_id)
        if category_id is not None and include_descendants:
            ctes.append(
                """
                descendants(id) AS (
                    SELECT id FROM categories WHERE id = ?
                    UNION ALL
                    SELECT c.id
                    FROM categories c
                    JOIN descendants d ON c.parent_id = d.id
                )
                """.strip()
            )
            params.insert(0, category_id)
            where.append(
                """
                EXISTS (
                    SELECT 1
                    FROM image_tags it
                    WHERE it.content_hash = images.content_hash
                      AND it.category_id IN (SELECT id FROM descendants)
                )
                """.strip()
            )
        elif category_id is not None:
            where.append(
                """
                EXISTS (
                    SELECT 1
                    FROM image_tags it
                    WHERE it.content_hash = images.content_hash
                      AND it.category_id = ?
                )
                """.strip()
            )
            params.append(category_id)
        if cursor is not None:
            where.append("images.canonical_path > ?")
            params.append(cursor)

        with_clause = f"WITH RECURSIVE {', '.join(ctes)} " if ctes else ""
        where_clause = f" WHERE {' AND '.join(where)}" if where else ""
        limit_clause = ""
        if limit is not None:
            limit_clause = " LIMIT ?"
            params.append(limit + 1)
        sql = (
            f"{with_clause}"
            "SELECT images.* FROM images"
            f"{where_clause}"
            " ORDER BY images.canonical_path ASC"
            f"{limit_clause}"
        )
        return sql, params

    def set_system_state(self, key: str, value: str) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO system_state (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def delete_system_state(self, key: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM system_state WHERE key = ?", (key,))

    def get_embedding_config(self) -> dict[str, str | None]:
        return {
            "provider": self.get_system_state(EMBEDDING_PROVIDER_STATE_KEY),
            "jina_api_key": self.get_system_state(JINA_API_KEY_STATE_KEY),
            "google_api_key": self.get_system_state(GOOGLE_API_KEY_STATE_KEY),
        }

    def set_embedding_config(
        self,
        *,
        provider: str | None = None,
        jina_api_key: str | None = None,
        google_api_key: str | None = None,
    ) -> None:
        if provider is not None:
            self.set_system_state(EMBEDDING_PROVIDER_STATE_KEY, provider)
        if jina_api_key is not None:
            self.set_system_state(JINA_API_KEY_STATE_KEY, jina_api_key)
        if google_api_key is not None:
            self.set_system_state(GOOGLE_API_KEY_STATE_KEY, google_api_key)

    def get_system_state(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM system_state WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"])

    def get_excluded_folders(self) -> list[str]:
        value = self.get_system_state("excluded_folders")
        if not value:
            return []
        try:
            folders = json.loads(value)
            if isinstance(folders, list):
                return [str(f) for f in folders if f]
        except (ValueError, TypeError):
            pass
        return []

    def set_excluded_folders(self, folders: list[str]) -> None:
        cleaned = sorted(set(f.strip("/") for f in folders if f.strip("/")))
        self.set_system_state("excluded_folders", json.dumps(cleaned))

    def _refresh_image_activity(
        self, connection: sqlite3.Connection, content_hash: str, seen_at: str
    ) -> None:
        existing_row = connection.execute(
            "SELECT canonical_path FROM images WHERE content_hash = ?",
            (content_hash,),
        ).fetchone()
        if existing_row is None:
            return
        active_paths = [
            str(row["path"])
            for row in connection.execute(
                """
                SELECT path
                FROM image_paths
                WHERE content_hash = ? AND is_active = 1
                ORDER BY path ASC
                """,
                (content_hash,),
            ).fetchall()
        ]
        canonical_path = choose_canonical_path(existing_row["canonical_path"], active_paths)
        if canonical_path is None:
            connection.execute(
                "UPDATE images SET is_active = 0, updated_at = ? WHERE content_hash = ?",
                (seen_at, content_hash),
            )
            return
        connection.execute(
            """
            UPDATE images
            SET canonical_path = ?, is_active = 1, last_seen_at = ?, updated_at = ?
            WHERE content_hash = ?
            """,
            (canonical_path, seen_at, seen_at, content_hash),
        )

    def _ensure_embedding_status_column(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("PRAGMA table_info(images)").fetchall()
        columns = {str(row["name"]) for row in rows}
        if "embedding_status" in columns:
            return
        connection.execute(
            """
            ALTER TABLE images
            ADD COLUMN embedding_status TEXT NOT NULL DEFAULT 'pending'
            """
        )
        connection.execute(
            """
            UPDATE images
            SET embedding_status = 'embedded'
            WHERE embedding_status = 'pending'
            """
        )

    def _ensure_album_schema(self, connection: sqlite3.Connection) -> None:
        table_names = {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if "albums" in table_names:
            album_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(albums)").fetchall()
            }
            if "description" not in album_columns:
                connection.execute(
                    "ALTER TABLE albums ADD COLUMN description TEXT NOT NULL DEFAULT ''"
                )
            if "updated_at" not in album_columns:
                connection.execute(
                    "ALTER TABLE albums ADD COLUMN updated_at TEXT"
                )
                connection.execute(
                    """
                    UPDATE albums
                    SET updated_at = COALESCE(updated_at, created_at)
                    """
                )

        if "album_images" in table_names:
            album_image_columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(album_images)").fetchall()
            }
            if "sort_order" not in album_image_columns:
                connection.execute(
                    "ALTER TABLE album_images ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
                )
            if "added_at" not in album_image_columns:
                connection.execute(
                    "ALTER TABLE album_images ADD COLUMN added_at TEXT"
                )
                if "created_at" in album_image_columns:
                    connection.execute(
                        """
                        UPDATE album_images
                        SET added_at = COALESCE(added_at, created_at)
                        """
                    )
                else:
                    now = _to_iso(datetime.now(timezone.utc))
                    connection.execute(
                        """
                        UPDATE album_images
                        SET added_at = COALESCE(added_at, ?)
                        """,
                        (now,),
                    )


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


def _row_to_image(row: sqlite3.Row) -> ImageRecord:
    return ImageRecord(
        content_hash=row["content_hash"],
        canonical_path=row["canonical_path"],
        file_size=int(row["file_size"]),
        mtime=float(row["mtime"]),
        mime_type=row["mime_type"],
        width=int(row["width"]),
        height=int(row["height"]),
        is_active=bool(row["is_active"]),
        last_seen_at=_from_iso(row["last_seen_at"]) or datetime.min,
        embedding_provider=row["embedding_provider"],
        embedding_model=row["embedding_model"],
        embedding_version=row["embedding_version"],
        embedding_status=row["embedding_status"],
        created_at=_from_iso(row["created_at"]) or datetime.min,
        updated_at=_from_iso(row["updated_at"]) or datetime.min,
    )




def _row_to_job(row: sqlite3.Row) -> JobRecord:
    return JobRecord(
        id=row["id"],
        job_type=row["job_type"],
        status=row["status"],
        requested_at=_from_iso(row["requested_at"]) or datetime.min,
        started_at=_from_iso(row["started_at"]),
        finished_at=_from_iso(row["finished_at"]),
        summary_json=row["summary_json"],
        error_text=row["error_text"],
    )


def _row_to_image_path(row: sqlite3.Row) -> ImagePathRecord:
    return ImagePathRecord(
        content_hash=row["content_hash"],
        path=row["path"],
        file_size=int(row["file_size"]),
        mtime=float(row["mtime"]),
        is_active=bool(row["is_active"]),
        last_seen_at=_from_iso(row["last_seen_at"]) or datetime.min,
        created_at=_from_iso(row["created_at"]) or datetime.min,
        updated_at=_from_iso(row["updated_at"]) or datetime.min,
    )


def _parse_album_images_cursor(cursor: str) -> tuple[int, int]:
    try:
        sort_order_text, album_image_id_text = cursor.split(":", 1)
        return int(sort_order_text), int(album_image_id_text)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid album image cursor") from exc
