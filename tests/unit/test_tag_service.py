import pytest
from unittest.mock import MagicMock
from image_search_mcp.services.tagging import TagService
from image_search_mcp.domain.models import Tag, Category, CategoryNode
from datetime import datetime, timezone


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class TestTagServiceValidation:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    def test_create_tag_empty_name_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_tag("")

    def test_create_tag_whitespace_only_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_tag("   ")

    def test_create_tag_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.create_tag.return_value = Tag(id=1, name="sunset", created_at=NOW)
        result = svc.create_tag("sunset")
        repo.create_tag.assert_called_once_with("sunset")
        assert result.name == "sunset"

    def test_create_category_empty_name_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="name"):
            svc.create_category("")

    def test_create_category_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.create_category.return_value = Category(
            id=1, name="Nature", parent_id=None, sort_order=0, created_at=NOW
        )
        result = svc.create_category("Nature")
        repo.create_category.assert_called_once_with("Nature", parent_id=None)
        assert result.name == "Nature"

    def test_move_category_to_self_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="itself"):
            svc.move_category(1, 1)


class TestBulkDeleteTags:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    def test_bulk_delete_tags_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_delete_tags.return_value = 3
        result = svc.bulk_delete_tags([1, 2, 3])
        repo.bulk_delete_tags.assert_called_once_with([1, 2, 3])
        assert result == 3

    def test_bulk_delete_tags_empty_list(self):
        svc, repo = self._make_service()
        repo.bulk_delete_tags.return_value = 0
        result = svc.bulk_delete_tags([])
        repo.bulk_delete_tags.assert_called_once_with([])
        assert result == 0

    def test_bulk_delete_tags_exceeds_max_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="maximum"):
            svc.bulk_delete_tags(list(range(501)))


class TestBulkDeleteCategories:
    def _make_service(self):
        repo = MagicMock()
        return TagService(repository=repo), repo

    def test_bulk_delete_categories_delegates_to_repo(self):
        svc, repo = self._make_service()
        repo.bulk_delete_categories.return_value = 5
        result = svc.bulk_delete_categories([10, 20])
        repo.bulk_delete_categories.assert_called_once_with([10, 20])
        assert result == 5

    def test_bulk_delete_categories_empty_list(self):
        svc, repo = self._make_service()
        repo.bulk_delete_categories.return_value = 0
        result = svc.bulk_delete_categories([])
        repo.bulk_delete_categories.assert_called_once_with([])
        assert result == 0

    def test_bulk_delete_categories_exceeds_max_raises(self):
        svc, repo = self._make_service()
        with pytest.raises(ValueError, match="maximum"):
            svc.bulk_delete_categories(list(range(501)))
