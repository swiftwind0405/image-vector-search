from image_vector_search.domain.models import Album, AlbumRule, PaginatedAlbumImages
from image_vector_search.repositories.sqlite import MetadataRepository


class AlbumService:
    MAX_BULK_SIZE = 500

    def __init__(self, *, repository: MetadataRepository) -> None:
        self._repo = repository

    def create_album(
        self,
        *,
        name: str,
        album_type: str,
        description: str | None = None,
        rule_logic: str | None = None,
    ) -> Album:
        name = name.strip()
        if not name:
            raise ValueError("Album name must not be empty")
        if album_type not in {"manual", "smart"}:
            raise ValueError("Album type must be 'manual' or 'smart'")
        if album_type == "manual":
            rule_logic = None
        elif rule_logic not in {"and", "or"}:
            raise ValueError("Smart albums require rule_logic of 'and' or 'or'")
        return self._repo.create_album(
            name=name,
            album_type=album_type,
            description=description,
            rule_logic=rule_logic,
        )

    def list_albums(self) -> list[Album]:
        return self._repo.list_albums()

    def get_album(self, album_id: int) -> Album | None:
        return self._repo.get_album(album_id)

    def update_album(
        self,
        *,
        album_id: int,
        name: str,
        description: str | None = None,
    ) -> Album | None:
        name = name.strip()
        if not name:
            raise ValueError("Album name must not be empty")
        return self._repo.update_album(album_id, name, description)

    def delete_album(self, album_id: int) -> None:
        self._repo.delete_album(album_id)

    def add_images_to_album(self, album_id: int, content_hashes: list[str]) -> int:
        album = self._require_album(album_id)
        if album.type != "manual":
            raise ValueError("Cannot add images to a smart album")
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.add_images_to_album(album_id, content_hashes)

    def remove_images_from_album(self, album_id: int, content_hashes: list[str]) -> int:
        album = self._require_album(album_id)
        if album.type != "manual":
            raise ValueError("Cannot remove images from a smart album")
        if len(content_hashes) > self.MAX_BULK_SIZE:
            raise ValueError(f"content_hashes exceeds maximum of {self.MAX_BULK_SIZE}")
        return self._repo.remove_images_from_album(album_id, content_hashes)

    def list_album_images(
        self,
        album_id: int,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedAlbumImages:
        album = self._require_album(album_id)
        if album.type == "manual":
            return self._repo.list_album_images(album_id, limit=limit, cursor=cursor)
        return self.list_smart_album_images(album_id, limit=limit, cursor=cursor)

    def set_album_rules(self, album_id: int, rules: list[dict[str, object]]) -> None:
        album = self._require_album(album_id)
        if album.type != "smart":
            raise ValueError("Cannot set rules for a manual album")
        tag_ids = [int(rule["tag_id"]) for rule in rules]
        if len(tag_ids) != len(set(tag_ids)):
            raise ValueError("Duplicate tag_id in album rules")
        self._repo.set_album_rules(album_id, rules)

    def get_album_rules(self, album_id: int) -> list[AlbumRule]:
        self._require_album(album_id)
        return self._repo.get_album_rules(album_id)

    def set_album_source_paths(self, album_id: int, paths: list[str]) -> None:
        album = self._require_album(album_id)
        if album.type != "smart":
            raise ValueError("Cannot set source paths for a manual album")
        normalized = [path.strip().strip("/") for path in paths if path.strip().strip("/")]
        self._repo.set_album_source_paths(album_id, normalized)

    def get_album_source_paths(self, album_id: int) -> list[str]:
        self._require_album(album_id)
        return self._repo.get_album_source_paths(album_id)

    def list_smart_album_images(
        self,
        album_id: int,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> PaginatedAlbumImages:
        album = self._require_album(album_id)
        if album.type != "smart":
            raise ValueError("Manual albums do not support smart album queries")
        return self._repo.list_smart_album_images(album_id, limit=limit, cursor=cursor)

    def _require_album(self, album_id: int) -> Album:
        album = self._repo.get_album(album_id)
        if album is None:
            raise ValueError(f"Album {album_id} not found")
        return album
