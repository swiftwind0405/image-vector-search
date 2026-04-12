import sqlite3

from image_vector_search.repositories.sqlite import MetadataRepository


def test_initialize_schema_migrates_legacy_album_tables(tmp_path):
    db_path = tmp_path / "metadata.sqlite3"
    repository = MetadataRepository(db_path)

    with repository.connect() as connection:
        connection.executescript(
            """
            CREATE TABLE albums (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              type TEXT NOT NULL,
              rule_logic TEXT,
              created_at TEXT NOT NULL
            );

            CREATE TABLE album_images (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              album_id INTEGER NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        connection.execute(
            """
            INSERT INTO albums (name, type, rule_logic, created_at)
            VALUES ('Legacy Album', 'manual', NULL, '2026-01-01T00:00:00+00:00')
            """
        )
        connection.execute(
            """
            INSERT INTO album_images (album_id, content_hash, created_at)
            VALUES (1, 'hash-a', '2026-01-01T00:00:00+00:00')
            """
        )

    repository.initialize_schema()

    with sqlite3.connect(db_path) as connection:
        album_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(albums)").fetchall()
        }
        album_image_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(album_images)").fetchall()
        }
        updated_at = connection.execute(
            "SELECT updated_at FROM albums WHERE id = 1"
        ).fetchone()[0]
        added_at = connection.execute(
            "SELECT added_at FROM album_images WHERE id = 1"
        ).fetchone()[0]

    assert {"description", "updated_at"}.issubset(album_columns)
    assert {"sort_order", "added_at"}.issubset(album_image_columns)
    assert updated_at == "2026-01-01T00:00:00+00:00"
    assert added_at == "2026-01-01T00:00:00+00:00"
