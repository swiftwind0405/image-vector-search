from __future__ import annotations

import re
import sqlite3

from image_vector_search.domain.models import Tag
from image_vector_search.repositories.sqlite import MetadataRepository


class TagService:
    MAX_BULK_SIZE = 500

    def __init__(self, *, repository: MetadataRepository) -> None:
        self._repo = repository

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

    def bulk_delete_tags(self, tag_ids: list[int]) -> int:
        if len(tag_ids) > self.MAX_BULK_SIZE:
            raise ValueError(f"tag_ids exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_delete_tags(tag_ids)

    def add_tag_to_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.add_tag_to_image(content_hash, tag_id)

    def remove_tag_from_image(self, content_hash: str, tag_id: int) -> None:
        self._repo.remove_tag_from_image(content_hash, tag_id)

    def get_image_tags(self, content_hash: str) -> list[Tag]:
        return self._repo.get_image_tags(content_hash)

    def bulk_add_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        try:
            return self._repo.bulk_add_tag(content_hashes, tag_id)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Invalid tag_id: {tag_id}") from exc

    def bulk_remove_tag(self, content_hashes: list[str], tag_id: int) -> int:
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.bulk_remove_tag(content_hashes, tag_id)

    def bulk_folder_add_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        try:
            return self._repo.bulk_folder_add_tag(folder, tag_id, images_root)
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"Invalid tag_id: {tag_id}") from exc

    def bulk_folder_remove_tag(self, folder: str, tag_id: int, images_root: str) -> int:
        return self._repo.bulk_folder_remove_tag(folder, tag_id, images_root)

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


_HEADING_RE = re.compile(r"^(#{2,6})\s+(.+)$")


def _parse_tag_headings(content: str) -> list[str]:
    names: list[str] = []
    for line in content.splitlines():
        match = _HEADING_RE.match(line)
        if match and len(match.group(1)) == 2:
            name = match.group(2).strip()
            if name:
                names.append(name)
    return names
