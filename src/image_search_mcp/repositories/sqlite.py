import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from image_search_mcp.domain.models import (
    Category,
    CategoryNode,
    ImagePathRecord,
    ImageRecord,
    ImageRecordWithLabels,
    JobRecord,
    StatusAggregates,
    Tag,
)


def choose_canonical_path(existing: str | None, active_paths: list[str]) -> str | None:
    if existing and existing in active_paths:
        return existing
    if not active_paths:
        return None
    return sorted(active_paths)[0]


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

    def upsert_image(self, image: ImageRecord) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO images (
                    content_hash, canonical_path, file_size, mtime, mime_type, width, height,
                    is_active, last_seen_at, embedding_provider, embedding_model, embedding_version,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def list_active_images(
        self,
        folder: str | None = None,
        images_root: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
    ) -> list[ImageRecord]:
        with self.connect() as connection:
            if folder is not None and images_root is not None:
                prefix = images_root.rstrip("/") + "/" + folder.strip("/") + "/"
                rows = connection.execute(
                    "SELECT * FROM images WHERE is_active = 1 AND canonical_path LIKE ? ORDER BY canonical_path ASC",
                    (prefix + "%",),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM images WHERE is_active = 1 ORDER BY canonical_path ASC"
                ).fetchall()
        images = [_row_to_image(row) for row in rows]
        if not images:
            return []

        allowed_hashes: set[str] | None = None
        if tag_id is not None:
            allowed_hashes = self.filter_by_tags([tag_id])
        if category_id is not None:
            category_hashes = self.filter_by_category(
                category_id,
                include_subcategories=include_descendants,
            )
            allowed_hashes = (
                category_hashes
                if allowed_hashes is None
                else allowed_hashes & category_hashes
            )
        if allowed_hashes is None:
            return images
        return [image for image in images if image.content_hash in allowed_hashes]

    def list_active_images_with_labels(
        self,
        folder: str | None = None,
        images_root: str | None = None,
        tag_id: int | None = None,
        category_id: int | None = None,
        include_descendants: bool = True,
    ) -> list[ImageRecordWithLabels]:
        images = self.list_active_images(
            folder=folder,
            images_root=images_root,
            tag_id=tag_id,
            category_id=category_id,
            include_descendants=include_descendants,
        )
        if not images:
            return []
        hashes = [img.content_hash for img in images]
        tags_map = self.get_tags_for_images(hashes)
        cats_map = self.get_categories_for_images(hashes)
        return [
            ImageRecordWithLabels(
                **img.model_dump(),
                tags=tags_map.get(img.content_hash, []),
                categories=cats_map.get(img.content_hash, []),
            )
            for img in images
        ]

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

    def get_system_state(self, key: str) -> str | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM system_state WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"])

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
