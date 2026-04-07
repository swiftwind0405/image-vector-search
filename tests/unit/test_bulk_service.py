import sqlite3
import pytest
from unittest.mock import MagicMock

from image_vector_search.services.tagging import TagService


class TestBulkTagService:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    # --- bulk_add_tag ---

    def test_bulk_add_tag_exceeds_max_raises(self):
        svc, repo = self._make_service()
        hashes = ["h"] * (TagService.MAX_BULK_SIZE + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            svc.bulk_add_tag(hashes, tag_id=1)
        repo.bulk_add_tag.assert_not_called()

    def test_bulk_add_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        hashes = ["aaa", "bbb"]
        repo.bulk_add_tag.return_value = 2
        result = svc.bulk_add_tag(hashes, tag_id=5)
        repo.bulk_add_tag.assert_called_once_with(hashes, 5)
        assert result == 2

    def test_bulk_add_tag_integrity_error_raises_value_error(self):
        svc, repo = self._make_service()
        repo.bulk_add_tag.side_effect = sqlite3.IntegrityError("fk")
        with pytest.raises(ValueError, match="Invalid tag_id: 99"):
            svc.bulk_add_tag(["abc"], tag_id=99)

    def test_bulk_add_tag_exactly_max_size_ok(self):
        svc, repo = self._make_service()
        hashes = ["h"] * TagService.MAX_BULK_SIZE
        repo.bulk_add_tag.return_value = TagService.MAX_BULK_SIZE
        result = svc.bulk_add_tag(hashes, tag_id=1)
        assert result == TagService.MAX_BULK_SIZE

    # --- bulk_remove_tag ---

    def test_bulk_remove_tag_exceeds_max_raises(self):
        svc, repo = self._make_service()
        hashes = ["h"] * (TagService.MAX_BULK_SIZE + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            svc.bulk_remove_tag(hashes, tag_id=1)
        repo.bulk_remove_tag.assert_not_called()

    def test_bulk_remove_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        hashes = ["aaa", "bbb"]
        repo.bulk_remove_tag.return_value = 2
        result = svc.bulk_remove_tag(hashes, tag_id=3)
        repo.bulk_remove_tag.assert_called_once_with(hashes, 3)
        assert result == 2

    # --- bulk_add_category ---

    def test_bulk_add_category_exceeds_max_raises(self):
        svc, repo = self._make_service()
        hashes = ["h"] * (TagService.MAX_BULK_SIZE + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            svc.bulk_add_category(hashes, category_id=1)
        repo.bulk_add_category.assert_not_called()

    def test_bulk_add_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        hashes = ["ccc"]
        repo.bulk_add_category.return_value = 1
        result = svc.bulk_add_category(hashes, category_id=7)
        repo.bulk_add_category.assert_called_once_with(hashes, 7)
        assert result == 1

    def test_bulk_add_category_integrity_error_raises_value_error(self):
        svc, repo = self._make_service()
        repo.bulk_add_category.side_effect = sqlite3.IntegrityError("fk")
        with pytest.raises(ValueError, match="Invalid category_id: 42"):
            svc.bulk_add_category(["abc"], category_id=42)

    def test_bulk_add_category_exactly_max_size_ok(self):
        svc, repo = self._make_service()
        hashes = ["h"] * TagService.MAX_BULK_SIZE
        repo.bulk_add_category.return_value = TagService.MAX_BULK_SIZE
        result = svc.bulk_add_category(hashes, category_id=1)
        assert result == TagService.MAX_BULK_SIZE

    # --- bulk_remove_category ---

    def test_bulk_remove_category_exceeds_max_raises(self):
        svc, repo = self._make_service()
        hashes = ["h"] * (TagService.MAX_BULK_SIZE + 1)
        with pytest.raises(ValueError, match="exceeds maximum"):
            svc.bulk_remove_category(hashes, category_id=1)
        repo.bulk_remove_category.assert_not_called()

    def test_bulk_remove_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        hashes = ["ddd", "eee"]
        repo.bulk_remove_category.return_value = 2
        result = svc.bulk_remove_category(hashes, category_id=4)
        repo.bulk_remove_category.assert_called_once_with(hashes, 4)
        assert result == 2

    # --- bulk_folder_add_tag ---

    def test_bulk_folder_add_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_tag.return_value = 10
        result = svc.bulk_folder_add_tag("nature", tag_id=2, images_root="/images")
        repo.bulk_folder_add_tag.assert_called_once_with("nature", 2, "/images")
        assert result == 10

    def test_bulk_folder_add_tag_integrity_error_raises_value_error(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_tag.side_effect = sqlite3.IntegrityError("fk")
        with pytest.raises(ValueError, match="Invalid tag_id: 77"):
            svc.bulk_folder_add_tag("nature", tag_id=77, images_root="/images")

    # --- bulk_folder_remove_tag ---

    def test_bulk_folder_remove_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_folder_remove_tag.return_value = 5
        result = svc.bulk_folder_remove_tag("nature", tag_id=2, images_root="/images")
        repo.bulk_folder_remove_tag.assert_called_once_with("nature", 2, "/images")
        assert result == 5

    # --- bulk_folder_add_category ---

    def test_bulk_folder_add_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_category.return_value = 8
        result = svc.bulk_folder_add_category("animals", category_id=3, images_root="/images")
        repo.bulk_folder_add_category.assert_called_once_with("animals", 3, "/images")
        assert result == 8

    def test_bulk_folder_add_category_integrity_error_raises_value_error(self):
        svc, repo = self._make_service()
        repo.bulk_folder_add_category.side_effect = sqlite3.IntegrityError("fk")
        with pytest.raises(ValueError, match="Invalid category_id: 55"):
            svc.bulk_folder_add_category("animals", category_id=55, images_root="/images")

    # --- bulk_folder_remove_category ---

    def test_bulk_folder_remove_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_folder_remove_category.return_value = 3
        result = svc.bulk_folder_remove_category("animals", category_id=3, images_root="/images")
        repo.bulk_folder_remove_category.assert_called_once_with("animals", 3, "/images")
        assert result == 3
