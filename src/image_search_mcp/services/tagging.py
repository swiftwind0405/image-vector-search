from __future__ import annotations

from image_search_mcp.domain.models import Tag, Category, CategoryNode
from image_search_mcp.repositories.sqlite import MetadataRepository


class TagService:
    def __init__(self, *, repository: MetadataRepository) -> None:
        self._repo = repository

    # --- Tags ---

    def create_tag(self, name: str) -> Tag:
        name = name.strip()
        if not name:
            raise ValueError("Tag name must not be empty")
        return self._repo.create_tag(name)

    def list_tags(self) -> list[Tag]:
        return self._repo.list_tags()

    def rename_tag(self, tag_id: int, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Tag name must not be empty")
        self._repo.rename_tag(tag_id, new_name)

    def delete_tag(self, tag_id: int) -> None:
        self._repo.delete_tag(tag_id)

    # --- Categories ---

    def create_category(self, name: str, parent_id: int | None = None) -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name must not be empty")
        return self._repo.create_category(name, parent_id=parent_id)

    def list_categories(self, parent_id: int | None = None) -> list[Category]:
        return self._repo.list_categories(parent_id=parent_id)

    def get_category_tree(self) -> list[CategoryNode]:
        return self._repo.get_category_tree()

    def rename_category(self, category_id: int, new_name: str) -> None:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Category name must not be empty")
        self._repo.rename_category(category_id, new_name)

    def move_category(self, category_id: int, new_parent_id: int | None) -> None:
        if new_parent_id == category_id:
            raise ValueError("Cannot move a category to itself")
        self._repo.move_category(category_id, new_parent_id)

    def delete_category(self, category_id: int) -> None:
        self._repo.delete_category(category_id)

    # --- Image associations ---

    def add_tag_to_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.add_tag_to_image(content_hash, tag_id)

    def remove_tag_from_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.remove_tag_from_image(content_hash, tag_id)

    def add_image_to_category(self, content_hash: str, category_id: int) -> None:
        self._repo.add_image_to_category(content_hash, category_id)

    def remove_image_from_category(self, content_hash: str, category_id: int) -> None:
        self._repo.remove_image_from_category(content_hash, category_id)

    def get_image_tags(self, content_hash: str) -> list[Tag]:
        return self._repo.get_image_tags(content_hash)

    def get_image_categories(self, content_hash: str) -> list[Category]:
        return self._repo.get_image_categories(content_hash)
