"""Tests for Task 1 & 2: Repository Bulk Methods and Folder-Bulk Methods."""
import pytest
from datetime import datetime, timezone

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _make_image(content_hash: str, canonical_path: str) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash, canonical_path=canonical_path,
        file_size=1000, mtime=1000.0, mime_type="image/jpeg",
        width=100, height=100, is_active=True, last_seen_at=NOW,
        embedding_provider="jina", embedding_model="jina-clip-v2",
        embedding_version="v2", created_at=NOW, updated_at=NOW,
    )


def _make_repo(tmp_path) -> MetadataRepository:
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    return repo


def _insert_image(repo: MetadataRepository, content_hash: str, canonical_path: str) -> None:
    repo.upsert_image(_make_image(content_hash, canonical_path))


# ---------------------------------------------------------------------------
# list_folders
# ---------------------------------------------------------------------------

class TestListFolders:
    def test_returns_empty_when_no_images(self, tmp_path):
        repo = _make_repo(tmp_path)
        assert repo.list_folders("/data/images") == []

    def test_returns_distinct_relative_folders(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/rose.jpg")
        _insert_image(repo, "h2", "/data/images/nature/tulip.jpg")
        _insert_image(repo, "h3", "/data/images/city/tower.jpg")
        result = repo.list_folders("/data/images")
        assert result == ["city", "nature"]

    def test_strips_images_root_prefix(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/sub/img.jpg")
        result = repo.list_folders("/data/images")
        assert result == ["sub"]

    def test_handles_trailing_slash_on_root(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/sub/img.jpg")
        result = repo.list_folders("/data/images/")
        assert result == ["sub"]

    def test_inactive_images_excluded(self, tmp_path):
        repo = _make_repo(tmp_path)
        # Insert active image
        _insert_image(repo, "h1", "/data/images/active/img.jpg")
        # Insert inactive image directly
        with repo.connect() as conn:
            conn.execute("""
                INSERT INTO images (content_hash, canonical_path, file_size, mtime, mime_type,
                    width, height, is_active, last_seen_at, embedding_provider, embedding_model,
                    embedding_version, created_at, updated_at)
                VALUES ('h2', '/data/images/inactive/img.jpg', 100, 1.0, 'image/jpeg', 100, 100, 0,
                    '2026-01-01T00:00:00+00:00', 'jina', 'jina-clip-v2', 'v2',
                    '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')
            """)
        result = repo.list_folders("/data/images")
        assert result == ["active"]

    def test_sorted_alphabetically(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/z_folder/img.jpg")
        _insert_image(repo, "h2", "/data/images/a_folder/img.jpg")
        _insert_image(repo, "h3", "/data/images/m_folder/img.jpg")
        result = repo.list_folders("/data/images")
        assert result == ["a_folder", "m_folder", "z_folder"]

    def test_nested_folders_use_immediate_parent(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/flowers/rose.jpg")
        result = repo.list_folders("/data/images")
        assert result == ["nature/flowers"]


# ---------------------------------------------------------------------------
# list_active_images with folder filter
# ---------------------------------------------------------------------------

class TestListActiveImagesWithFolder:
    def test_no_args_returns_all_active(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/a/img.jpg")
        _insert_image(repo, "h2", "/data/images/b/img.jpg")
        result = repo.list_active_images()
        assert len(result) == 2

    def test_folder_filters_by_prefix(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/rose.jpg")
        _insert_image(repo, "h2", "/data/images/city/tower.jpg")
        result = repo.list_active_images(folder="nature", images_root="/data/images")
        assert len(result) == 1
        assert result[0].content_hash == "h1"

    def test_folder_filter_matches_subfolders(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/flowers/rose.jpg")
        _insert_image(repo, "h2", "/data/images/nature/trees/oak.jpg")
        _insert_image(repo, "h3", "/data/images/city/tower.jpg")
        result = repo.list_active_images(folder="nature", images_root="/data/images")
        assert len(result) == 2
        hashes = {r.content_hash for r in result}
        assert hashes == {"h1", "h2"}

    def test_folder_none_returns_all(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/a/img.jpg")
        _insert_image(repo, "h2", "/data/images/b/img.jpg")
        result = repo.list_active_images(folder=None, images_root="/data/images")
        assert len(result) == 2

    def test_folder_with_trailing_slash_in_root(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/sub/img.jpg")
        _insert_image(repo, "h2", "/data/images/other/img.jpg")
        result = repo.list_active_images(folder="sub", images_root="/data/images/")
        assert len(result) == 1
        assert result[0].content_hash == "h1"

    def test_folder_with_leading_slash_stripped(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/sub/img.jpg")
        _insert_image(repo, "h2", "/data/images/other/img.jpg")
        result = repo.list_active_images(folder="/sub", images_root="/data/images")
        assert len(result) == 1
        assert result[0].content_hash == "h1"


# ---------------------------------------------------------------------------
# bulk_add_tag / bulk_remove_tag
# ---------------------------------------------------------------------------

class TestBulkAddRemoveTag:
    def _setup(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/img1.jpg")
        _insert_image(repo, "h2", "/data/images/img2.jpg")
        _insert_image(repo, "h3", "/data/images/img3.jpg")
        tag = repo.create_tag("sunset")
        return repo, tag

    def test_bulk_add_tag_returns_affected_count(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_add_tag(["h1", "h2"], tag.id)
        assert count == 2

    def test_bulk_add_tag_applies_to_all_hashes(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.bulk_add_tag(["h1", "h2", "h3"], tag.id)
        assert len(repo.get_image_tags("h1")) == 1
        assert len(repo.get_image_tags("h2")) == 1
        assert len(repo.get_image_tags("h3")) == 1

    def test_bulk_add_tag_ignores_duplicates(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.add_tag_to_image("h1", tag.id)
        # Should not raise — INSERT OR IGNORE
        count = repo.bulk_add_tag(["h1", "h2"], tag.id)
        # h1 already had it, so only h2 is new
        assert count == 1

    def test_bulk_add_tag_empty_list_returns_zero(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_add_tag([], tag.id)
        assert count == 0

    def test_bulk_remove_tag_returns_affected_count(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.add_tag_to_image("h1", tag.id)
        repo.add_tag_to_image("h2", tag.id)
        count = repo.bulk_remove_tag(["h1", "h2"], tag.id)
        assert count == 2

    def test_bulk_remove_tag_removes_correct_images(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.add_tag_to_image("h1", tag.id)
        repo.add_tag_to_image("h2", tag.id)
        repo.add_tag_to_image("h3", tag.id)
        repo.bulk_remove_tag(["h1", "h2"], tag.id)
        assert repo.get_image_tags("h1") == []
        assert repo.get_image_tags("h2") == []
        assert len(repo.get_image_tags("h3")) == 1

    def test_bulk_remove_tag_empty_list_returns_zero(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_remove_tag([], tag.id)
        assert count == 0

    def test_bulk_remove_nonexistent_tag_returns_zero(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        # Tag not added to any image
        count = repo.bulk_remove_tag(["h1", "h2"], tag.id)
        assert count == 0


# ---------------------------------------------------------------------------
# Folder-bulk methods (Task 2)
# ---------------------------------------------------------------------------

class TestFolderBulkTag:
    IMAGES_ROOT = "/data/images"

    def _setup(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/rose.jpg")
        _insert_image(repo, "h2", "/data/images/nature/tulip.jpg")
        _insert_image(repo, "h3", "/data/images/city/tower.jpg")
        tag = repo.create_tag("outdoors")
        return repo, tag

    def test_bulk_folder_add_tag_adds_to_folder_images(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_folder_add_tag("nature", tag.id, self.IMAGES_ROOT)
        assert count == 2
        assert len(repo.get_image_tags("h1")) == 1
        assert len(repo.get_image_tags("h2")) == 1
        assert repo.get_image_tags("h3") == []

    def test_bulk_folder_add_tag_returns_zero_for_empty_folder(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_folder_add_tag("nonexistent", tag.id, self.IMAGES_ROOT)
        assert count == 0

    def test_bulk_folder_add_tag_ignores_duplicates(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.add_tag_to_image("h1", tag.id)
        count = repo.bulk_folder_add_tag("nature", tag.id, self.IMAGES_ROOT)
        assert count == 1  # only h2 is new

    def test_bulk_folder_remove_tag_removes_from_folder_images(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        repo.add_tag_to_image("h1", tag.id)
        repo.add_tag_to_image("h2", tag.id)
        repo.add_tag_to_image("h3", tag.id)
        count = repo.bulk_folder_remove_tag("nature", tag.id, self.IMAGES_ROOT)
        assert count == 2
        assert repo.get_image_tags("h1") == []
        assert repo.get_image_tags("h2") == []
        assert len(repo.get_image_tags("h3")) == 1

    def test_bulk_folder_remove_tag_returns_zero_when_not_tagged(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_folder_remove_tag("nature", tag.id, self.IMAGES_ROOT)
        assert count == 0

    def test_bulk_folder_add_tag_handles_trailing_slash_on_root(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_folder_add_tag("nature", tag.id, "/data/images/")
        assert count == 2

    def test_bulk_folder_add_tag_handles_leading_slash_on_folder(self, tmp_path):
        repo, tag = self._setup(tmp_path)
        count = repo.bulk_folder_add_tag("/nature", tag.id, self.IMAGES_ROOT)
        assert count == 2

    def test_bulk_folder_add_tag_covers_subfolder_images(self, tmp_path):
        repo = _make_repo(tmp_path)
        _insert_image(repo, "h1", "/data/images/nature/flowers/rose.jpg")
        _insert_image(repo, "h2", "/data/images/nature/trees/oak.jpg")
        _insert_image(repo, "h3", "/data/images/city/tower.jpg")
        tag = repo.create_tag("green")
        count = repo.bulk_folder_add_tag("nature", tag.id, self.IMAGES_ROOT)
        assert count == 2

