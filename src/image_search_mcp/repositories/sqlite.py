import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from image_search_mcp.domain.models import (
    ImagePathRecord,
    ImageRecord,
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
            rows = conn.execute("SELECT id, name, created_at FROM tags ORDER BY name").fetchall()
            return [Tag(id=r["id"], name=r["name"], created_at=_from_iso(r["created_at"])) for r in rows]

    def rename_tag(self, tag_id: int, new_name: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE tags SET name = ? WHERE id = ?", (new_name, tag_id))

    def delete_tag(self, tag_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))

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
