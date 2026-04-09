from __future__ import annotations

import re
import sqlite3

from image_vector_search.domain.models import Tag, Category, CategoryNode
from image_vector_search.repositories.sqlite import MetadataRepository


class TagService:
    MAX_BULK_SIZE = 500

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

    # --- Bulk delete ---

    def bulk_delete_tags(self, tag_ids: list[int]) -> int:
        if len(tag_ids) > self.MAX_BULK_SIZE:
            raise ValueError(f"tag_ids exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_delete_tags(tag_ids)

    def bulk_delete_categories(self, category_ids: list[int]) -> int:
        if len(category_ids) > self.MAX_BULK_SIZE:
            raise ValueError(f"category_ids exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_delete_categories(category_ids)

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

    # --- Bulk operations ---

    def bulk_add_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        try:
            return self._repo.bulk_add_tag(content_hashes, tag_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Invalid tag_id: {tag_id}")

    def bulk_remove_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_remove_tag(content_hashes, tag_id)

    def bulk_add_category(self, content_hashes: list[str], category_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        try:
            return self._repo.bulk_add_category(content_hashes, category_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Invalid category_id: {category_id}")

    def bulk_remove_category(self, content_hashes: list[str], category_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_remove_category(content_hashes, category_id)

    def bulk_folder_add_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        try:
            return self._repo.bulk_folder_add_tag(folder, tag_id, images_root)
        except sqlite3.IntegrityError:
            raise ValueError(f"Invalid tag_id: {tag_id}")

    def bulk_folder_remove_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        return self._repo.bulk_folder_remove_tag(folder, tag_id, images_root)

    def bulk_folder_add_category(self, folder: str, category_id: int, images_root: str) -> int:
        try:
            return self._repo.bulk_folder_add_category(folder, category_id, images_root)
        except sqlite3.IntegrityError:
            raise ValueError(f"Invalid category_id: {category_id}")

    def bulk_folder_remove_category(self, folder: str, category_id: int, images_root: str) -> int:
        return self._repo.bulk_folder_remove_category(folder, category_id, images_root)

    # --- Markdown export/import ---

    def export_tags_markdown(self) -> str:
        tags = self._repo.list_tags()
        lines = ["# Tags", ""]
        for tag in tags:
            lines.append(f"## {tag.name}")
            lines.append("")
        return "\n".join(lines)

    def import_tags_markdown(self, content: str) -> dict[str, int]:
        names = _parse_tag_headings(content)
        existing = {t.name for t in self._repo.list_tags()}
        created = 0
        skipped = 0
        for name in names:
            if name in existing:
                skipped += 1
            else:
                self._repo.create_tag(name)
                existing.add(name)
                created += 1
        return {"created": created, "skipped": skipped}

    def export_categories_markdown(self) -> str:
        tree = self._repo.get_category_tree()
        lines = ["# Categories", ""]
        _render_category_tree(tree, lines, depth=0)
        return "\n".join(lines)

    def import_categories_markdown(self, content: str) -> dict[str, int]:
        items = _parse_heading_tree(content)
        created = 0
        skipped = 0

        def _import_level(
            items: list[tuple[str, list]],
            parent_id: int | None,
        ) -> None:
            nonlocal created, skipped
            siblings = self._repo.list_categories(parent_id=parent_id)
            existing = {c.name: c.id for c in siblings}
            for name, children in items:
                if name in existing:
                    skipped += 1
                    cat_id = existing[name]
                else:
                    cat = self._repo.create_category(name, parent_id=parent_id)
                    created += 1
                    cat_id = cat.id
                if children:
                    _import_level(children, cat_id)

        _import_level(items, None)
        return {"created": created, "skipped": skipped}


# ---- Markdown helpers ----

# Match heading lines: "## Title" through "###### Title"
_HEADING_RE = re.compile(r"^(#{2,6})\s+(.+)$")

_MAX_CATEGORY_DEPTH = 5  # h2..h6


def _parse_tag_headings(content: str) -> list[str]:
    """Extract h2 heading texts as tag names. Other content is ignored."""
    names: list[str] = []
    for line in content.splitlines():
        m = _HEADING_RE.match(line)
        if m and len(m.group(1)) == 2:
            name = m.group(2).strip()
            if name:
                names.append(name)
    return names


def _parse_heading_tree(content: str) -> list[tuple[str, list]]:
    """Parse heading hierarchy (h2..h6) into a nested tree.

    Returns list of (name, children) tuples. Max 5 levels deep.
    """
    entries: list[tuple[int, str]] = []  # (level, name)  level: 2..6
    for line in content.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))  # 2..6
            name = m.group(2).strip()
            if name:
                entries.append((level, name))

    def _build(
        items: list[tuple[int, str]], start: int, parent_level: int,
    ) -> tuple[list[tuple[str, list]], int]:
        result: list[tuple[str, list]] = []
        i = start
        while i < len(items):
            level, name = items[i]
            if level <= parent_level:
                break
            if level == parent_level + 1:
                i += 1
                children, i = _build(items, i, level)
                result.append((name, children))
            else:
                # skip unexpected deeper headings without parent
                i += 1
        return result, i

    # Categories start at h2 (level 1), so parent_level is 1
    tree, _ = _build(entries, 0, 1)
    return tree


def _render_category_tree(
    nodes: list[CategoryNode],
    lines: list[str],
    depth: int,
) -> None:
    if depth >= _MAX_CATEGORY_DEPTH:
        return
    prefix = "#" * (depth + 2)  # depth 0 → ##, depth 1 → ###, ... depth 4 → ######
    for node in nodes:
        lines.append(f"{prefix} {node.name}")
        lines.append("")
        if node.children:
            _render_category_tree(node.children, lines, depth + 1)

