import sqlite3
from pathlib import Path

from image_search_mcp.domain.models import SearchFilters, SearchResult


def test_search_filters_defaults() -> None:
    filters = SearchFilters()
    assert filters.folder is None
    assert filters.top_k == 5
    assert filters.min_score == 0.0


def test_search_filters_accepts_explicit_values() -> None:
    filters = SearchFilters(folder="/data/images/2024", top_k=3, min_score=0.2)
    assert filters.folder == "/data/images/2024"
    assert filters.top_k == 3
    assert filters.min_score == 0.2


def test_search_result_serialization() -> None:
    result = SearchResult(
        content_hash="abc",
        path="/data/images/a.jpg",
        score=0.9,
        width=100,
        height=80,
        mime_type="image/jpeg",
    )
    assert result.model_dump()["content_hash"] == "abc"


def test_schema_image_paths_has_content_hash_fk_and_index() -> None:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "src/image_search_mcp/repositories/schema.sql"
    )
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema_path.read_text(encoding="utf-8"))

        foreign_keys = conn.execute(
            "PRAGMA foreign_key_list('image_paths')"
        ).fetchall()
        assert any(
            row[2] == "images" and row[3] == "content_hash" and row[4] == "content_hash"
            for row in foreign_keys
        )

        index_names = [row[1] for row in conn.execute("PRAGMA index_list('image_paths')")]
        assert any(
            "content_hash"
            in [col[2] for col in conn.execute(f"PRAGMA index_info('{index_name}')")]
            for index_name in index_names
        )
    finally:
        conn.close()
