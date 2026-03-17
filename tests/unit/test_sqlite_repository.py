import pytest
from datetime import datetime

from image_search_mcp.domain.models import ImagePathRecord, ImageRecord, JobRecord
from image_search_mcp.repositories.sqlite import MetadataRepository, choose_canonical_path


def _build_repository(tmp_path):
    repository = MetadataRepository(tmp_path / "metadata.sqlite3")
    repository.initialize_schema()
    return repository


def _build_image(
    *,
    content_hash: str,
    canonical_path: str,
    is_active: bool = True,
    last_seen_at: datetime | None = None,
) -> ImageRecord:
    observed_at = last_seen_at or datetime(2026, 1, 1, 10, 0, 0)
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=100,
        mtime=1700000000.0,
        mime_type="image/jpeg",
        width=640,
        height=480,
        is_active=is_active,
        last_seen_at=observed_at,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v1",
        created_at=observed_at,
        updated_at=observed_at,
    )


def _build_path(
    *,
    content_hash: str,
    path: str,
    is_active: bool = True,
    last_seen_at: datetime | None = None,
) -> ImagePathRecord:
    observed_at = last_seen_at or datetime(2026, 1, 1, 10, 0, 0)
    return ImagePathRecord(
        content_hash=content_hash,
        path=path,
        file_size=100,
        mtime=1700000000.0,
        is_active=is_active,
        last_seen_at=observed_at,
        created_at=observed_at,
        updated_at=observed_at,
    )


def test_choose_canonical_path_keeps_existing_active_path():
    existing = "/data/images/2024/a.jpg"
    active_paths = ["/data/images/2024/a.jpg", "/data/images/2024/b.jpg"]
    assert choose_canonical_path(existing, active_paths) == existing


def test_choose_canonical_path_falls_back_to_sorted_active_path():
    active_paths = ["/data/images/z.jpg", "/data/images/a.jpg"]
    assert choose_canonical_path(None, active_paths) == "/data/images/a.jpg"


def test_initialize_schema_creates_core_tables(tmp_path):
    repository = _build_repository(tmp_path)

    with repository.connect() as connection:
        names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    assert {"images", "image_paths", "jobs", "system_state"}.issubset(names)


def test_connect_enables_sqlite_foreign_keys(tmp_path):
    repository = _build_repository(tmp_path)

    with repository.connect() as connection:
        foreign_keys_enabled = connection.execute("PRAGMA foreign_keys").fetchone()[0]

    assert foreign_keys_enabled == 1


def test_upsert_image_and_image_paths_list_only_active_paths(tmp_path):
    repository = _build_repository(tmp_path)
    content_hash = "hash-a"
    repository.upsert_image(
        _build_image(content_hash=content_hash, canonical_path="/data/images/b.jpg")
    )
    repository.upsert_image_path(
        _build_path(content_hash=content_hash, path="/data/images/b.jpg")
    )
    repository.upsert_image_path(
        _build_path(content_hash=content_hash, path="/data/images/a.jpg")
    )
    repository.upsert_image_path(
        _build_path(
            content_hash=content_hash,
            path="/data/images/old.jpg",
            is_active=False,
        )
    )

    assert repository.list_active_paths(content_hash) == [
        "/data/images/a.jpg",
        "/data/images/b.jpg",
    ]


def test_reassigning_path_to_new_hash_deactivates_old_image_row(tmp_path):
    repository = _build_repository(tmp_path)
    observed_at = datetime(2026, 1, 1, 10, 0, 0)

    repository.upsert_image(
        _build_image(
            content_hash="old-hash",
            canonical_path="/data/images/shared.jpg",
            last_seen_at=observed_at,
        )
    )
    repository.upsert_image(
        _build_image(
            content_hash="new-hash",
            canonical_path="/data/images/shared.jpg",
            last_seen_at=observed_at,
        )
    )
    repository.upsert_image_path(
        _build_path(
            content_hash="old-hash",
            path="/data/images/shared.jpg",
            last_seen_at=observed_at,
        )
    )
    repository.upsert_image_path(
        _build_path(
            content_hash="new-hash",
            path="/data/images/shared.jpg",
            last_seen_at=datetime(2026, 1, 1, 10, 5, 0),
        )
    )

    old_image = repository.get_image("old-hash")
    new_image = repository.get_image("new-hash")

    assert old_image is not None
    assert old_image.is_active is False
    assert repository.list_active_paths("old-hash") == []

    assert new_image is not None
    assert new_image.is_active is True
    assert new_image.canonical_path == "/data/images/shared.jpg"
    assert repository.list_active_paths("new-hash") == ["/data/images/shared.jpg"]


def test_mark_unseen_paths_inactive_updates_canonical_path_and_activity(tmp_path):
    repository = _build_repository(tmp_path)
    content_hash = "hash-b"
    repository.upsert_image(
        _build_image(content_hash=content_hash, canonical_path="/data/images/z.jpg")
    )
    repository.upsert_image_path(
        _build_path(content_hash=content_hash, path="/data/images/z.jpg")
    )
    repository.upsert_image_path(
        _build_path(content_hash=content_hash, path="/data/images/a.jpg")
    )

    repository.mark_unseen_paths_inactive(
        seen_paths=["/data/images/a.jpg"],
        seen_at=datetime(2026, 1, 1, 11, 0, 0),
    )
    image = repository.get_image(content_hash)
    assert image is not None
    assert image.canonical_path == "/data/images/a.jpg"
    assert image.is_active is True

    repository.mark_unseen_paths_inactive(
        seen_paths=[],
        seen_at=datetime(2026, 1, 1, 12, 0, 0),
    )
    image = repository.get_image(content_hash)
    assert image is not None
    assert image.is_active is False
    assert repository.list_active_paths(content_hash) == []


def test_read_status_aggregates_returns_image_counts(tmp_path):
    repository = _build_repository(tmp_path)
    repository.upsert_image(
        _build_image(content_hash="active", canonical_path="/data/images/a.jpg")
    )
    repository.upsert_image(
        _build_image(
            content_hash="inactive",
            canonical_path="/data/images/i.jpg",
            is_active=False,
        )
    )

    status = repository.read_status_aggregates()

    assert status.total_images == 2
    assert status.active_images == 1
    assert status.inactive_images == 1


def test_create_and_update_job_record(tmp_path):
    repository = _build_repository(tmp_path)
    requested_at = datetime(2026, 1, 1, 9, 0, 0)
    started_at = datetime(2026, 1, 1, 9, 1, 0)
    finished_at = datetime(2026, 1, 1, 9, 2, 0)
    repository.create_job(
        JobRecord(
            id="job-1",
            job_type="incremental",
            status="queued",
            requested_at=requested_at,
        )
    )

    repository.update_job(
        "job-1",
        status="succeeded",
        started_at=started_at,
        finished_at=finished_at,
        summary_json='{"indexed": 2}',
    )
    job = repository.get_job("job-1")

    assert job is not None
    assert job.status == "succeeded"
    assert job.started_at == started_at
    assert job.finished_at == finished_at
    assert job.summary_json == '{"indexed": 2}'


def test_update_job_preserves_started_at_when_later_update_omits_it(tmp_path):
    repository = _build_repository(tmp_path)
    requested_at = datetime(2026, 1, 1, 9, 0, 0)
    started_at = datetime(2026, 1, 1, 9, 1, 0)
    finished_at = datetime(2026, 1, 1, 9, 2, 0)
    repository.create_job(
        JobRecord(
            id="job-2",
            job_type="incremental",
            status="queued",
            requested_at=requested_at,
        )
    )

    repository.update_job("job-2", status="running", started_at=started_at)
    repository.update_job("job-2", status="succeeded", finished_at=finished_at)
    job = repository.get_job("job-2")

    assert job is not None
    assert job.status == "succeeded"
    assert job.started_at == started_at
    assert job.finished_at == finished_at


class TestTaggingSchema:
    def test_tags_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
            assert cursor.fetchone() is not None

    def test_categories_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='categories'")
            assert cursor.fetchone() is not None

    def test_image_tags_table_exists(self, tmp_path):
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='image_tags'")
            assert cursor.fetchone() is not None

    def test_image_tags_check_constraint(self, tmp_path):
        """Both tag_id and category_id NULL should fail."""
        repo = MetadataRepository(tmp_path / "test.db")
        repo.initialize_schema()
        with repo.connect() as conn:
            conn.execute("INSERT INTO tags (name, created_at) VALUES ('test', '2026-01-01T00:00:00+00:00')")
            conn.execute("""
                INSERT INTO images (content_hash, canonical_path, file_size, mtime, mime_type,
                    width, height, is_active, last_seen_at, embedding_provider, embedding_model,
                    embedding_version, created_at, updated_at)
                VALUES ('abc123', '/test.jpg', 100, 1.0, 'image/jpeg', 100, 100, 1,
                    '2026-01-01T00:00:00+00:00', 'jina', 'jina-clip-v2', 'v2',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """)
            conn.execute("""
                INSERT INTO image_tags (content_hash, tag_id, category_id, created_at)
                VALUES ('abc123', 1, NULL, '2026-01-01T00:00:00+00:00')
            """)
            import sqlite3
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO image_tags (content_hash, tag_id, category_id, created_at)
                    VALUES ('abc123', NULL, NULL, '2026-01-01T00:00:00+00:00')
                """)
