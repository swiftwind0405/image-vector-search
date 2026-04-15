from datetime import UTC, datetime

import pytest

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository

IMAGES_ROOT = "/data/images"


def _build_repo(tmp_path) -> MetadataRepository:
    return MetadataRepository(tmp_path / "metadata.sqlite3", images_root=IMAGES_ROOT)


def _build_image(content_hash: str, canonical_path: str) -> ImageRecord:
    now = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=100,
        mtime=1700000000.0,
        mime_type="image/jpeg",
        width=640,
        height=480,
        is_active=True,
        last_seen_at=now,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v1",
        embedding_status="embedded",
        created_at=now,
        updated_at=now,
    )


def _seed(repo: MetadataRepository, *items: tuple[str, str]) -> None:
    for content_hash, canonical_path in items:
        repo.upsert_image(_build_image(content_hash, canonical_path))


def test_excluded_path_clause_empty_when_no_exclusions(tmp_path):
    repo = _build_repo(tmp_path)
    sql, params = repo._excluded_path_clause()
    assert sql == ""
    assert params == []


def test_excluded_path_clause_empty_when_no_images_root(tmp_path):
    repo = MetadataRepository(tmp_path / "metadata.sqlite3")
    repo.set_excluded_folders(["junk"])
    sql, params = repo._excluded_path_clause()
    assert sql == ""
    assert params == []


def test_excluded_path_clause_escapes_like_metacharacters(tmp_path):
    repo = _build_repo(tmp_path)
    repo.set_excluded_folders(["weird_name%"])
    sql, params = repo._excluded_path_clause()
    assert "ESCAPE '\\'" in sql
    assert params == [r"/data/images/weird\_name\%/%"]


def test_list_active_images_filters_excluded_folder(tmp_path):
    repo = _build_repo(tmp_path)
    _seed(
        repo,
        ("h1", "/data/images/keep/a.jpg"),
        ("h2", "/data/images/junk/b.jpg"),
        ("h3", "/data/images/keep/sub/c.jpg"),
    )
    repo.set_excluded_folders(["junk"])

    paths = sorted(img.canonical_path for img in repo.list_active_images())
    assert paths == ["/data/images/keep/a.jpg", "/data/images/keep/sub/c.jpg"]


def test_list_images_in_folder_filters_excluded_subfolder(tmp_path):
    repo = _build_repo(tmp_path)
    _seed(
        repo,
        ("h1", "/data/images/2024/keep.jpg"),
        ("h2", "/data/images/2024/skip.jpg"),
    )
    repo.set_excluded_folders(["2024/skip.jpg"])  # not a folder, no-op
    rows = repo.list_images_in_folder("2024", IMAGES_ROOT)
    assert len(rows) == 2

    repo.set_excluded_folders(["2024"])
    rows = repo.list_images_in_folder("2024", IMAGES_ROOT)
    assert rows == []


def test_list_folders_omits_excluded(tmp_path):
    repo = _build_repo(tmp_path)
    _seed(
        repo,
        ("h1", "/data/images/keep/a.jpg"),
        ("h2", "/data/images/junk/b.jpg"),
        ("h3", "/data/images/junk/nested/c.jpg"),
    )
    repo.set_excluded_folders(["junk"])
    assert repo.list_folders(IMAGES_ROOT) == ["keep"]


def test_manual_album_count_and_listing_respect_exclusions(tmp_path):
    repo = _build_repo(tmp_path)
    _seed(
        repo,
        ("h1", "/data/images/keep/a.jpg"),
        ("h2", "/data/images/junk/b.jpg"),
    )
    album = repo.create_album(name="A", album_type="manual")
    repo.add_images_to_album(album.id, ["h1", "h2"])

    repo.set_excluded_folders(["junk"])
    fetched = repo.get_album(album.id)
    assert fetched.image_count == 1
    assert fetched.cover_image is not None
    assert fetched.cover_image.canonical_path == "/data/images/keep/a.jpg"

    page = repo.list_album_images(album.id)
    assert [img.content_hash for img in page.items] == ["h1"]


def test_smart_album_filters_exclusions(tmp_path):
    repo = _build_repo(tmp_path)
    tag = repo.create_tag("favorite")
    _seed(
        repo,
        ("h1", "/data/images/keep/a.jpg"),
        ("h2", "/data/images/junk/b.jpg"),
    )
    repo.add_tag_to_image("h1", tag.id)
    repo.add_tag_to_image("h2", tag.id)

    album = repo.create_album(name="Favs", album_type="smart", rule_logic="and")
    repo.set_album_rules(
        album.id, [{"tag_id": tag.id, "match_mode": "include"}]
    )

    repo.set_excluded_folders(["junk"])
    assert repo.count_smart_album_images(album.id) == 1
    page = repo.list_smart_album_images(album.id)
    assert [img.content_hash for img in page.items] == ["h1"]


def test_search_service_drops_results_under_excluded_folder():
    from pathlib import Path
    from types import SimpleNamespace

    from image_vector_search.services.search import SearchService

    settings = SimpleNamespace(
        images_root=Path(IMAGES_ROOT),
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v1",
    )

    keep = _build_image("h1", "/data/images/keep/a.jpg")
    junk = _build_image("h2", "/data/images/junk/b.jpg")

    class StubRepo:
        def __init__(self):
            self.excluded: list[str] = []

        def get_image(self, content_hash):
            return {"h1": keep, "h2": junk}.get(content_hash)

        def get_excluded_folders(self):
            return self.excluded

    repo = StubRepo()
    service = SearchService(
        settings=settings,
        repository=repo,
        embedding_client=None,
        vector_index=None,
    )

    raw = [
        {"content_hash": "h2", "score": 0.99},
        {"content_hash": "h1", "score": 0.5},
    ]
    results = service._resolve_results(
        raw_results=raw, folder=None, top_k=10, min_score=0.0
    )
    assert [r.content_hash for r in results] == ["h2", "h1"]

    repo.excluded = ["junk"]
    results = service._resolve_results(
        raw_results=raw, folder=None, top_k=10, min_score=0.0
    )
    assert [r.content_hash for r in results] == ["h1"]
