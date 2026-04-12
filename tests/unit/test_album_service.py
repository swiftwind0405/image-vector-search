import sqlite3
from datetime import UTC, datetime

import pytest

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository
from image_vector_search.services.albums import AlbumService


def _build_repository(tmp_path):
    repository = MetadataRepository(tmp_path / "metadata.sqlite3")
    repository.initialize_schema()
    return repository


def _build_image(*, content_hash: str, canonical_path: str) -> ImageRecord:
    observed_at = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=100,
        mtime=1700000000.0,
        mime_type="image/jpeg",
        width=640,
        height=480,
        is_active=True,
        last_seen_at=observed_at,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v1",
        embedding_status="embedded",
        created_at=observed_at,
        updated_at=observed_at,
    )


@pytest.fixture
def repository(tmp_path):
    return _build_repository(tmp_path)


@pytest.fixture
def service(repository):
    return AlbumService(repository=repository)


def _seed_images(repository: MetadataRepository, count: int) -> list[str]:
    hashes: list[str] = []
    for index in range(count):
        content_hash = f"hash-{index}"
        hashes.append(content_hash)
        repository.upsert_image(
            _build_image(
                content_hash=content_hash,
                canonical_path=f"/data/images/album/image-{index:03d}.jpg",
            )
        )
    return hashes


def test_create_manual_album(service: AlbumService):
    album = service.create_album(name="Vacation 2025", album_type="manual")

    assert album.id > 0
    assert album.name == "Vacation 2025"
    assert album.type == "manual"
    assert album.rule_logic is None
    assert album.image_count == 0


def test_create_smart_album_with_and_logic(service: AlbumService, repository: MetadataRepository):
    repository.create_tag("sunset")
    repository.create_tag("beach")
    repository.create_tag("mountain")

    album = service.create_album(
        name="Beach Sunsets",
        album_type="smart",
        rule_logic="and",
    )

    assert album.type == "smart"
    assert album.rule_logic == "and"


def test_create_smart_album_with_or_logic(service: AlbumService, repository: MetadataRepository):
    repository.create_tag("cat")
    repository.create_tag("dog")

    album = service.create_album(name="Pets", album_type="smart", rule_logic="or")

    assert album.type == "smart"
    assert album.rule_logic == "or"


def test_album_name_must_be_unique(service: AlbumService):
    service.create_album(name="My Album", album_type="manual")

    with pytest.raises(sqlite3.IntegrityError):
        service.create_album(name="My Album", album_type="manual")


def test_album_name_must_not_be_empty(service: AlbumService):
    with pytest.raises(ValueError, match="name"):
        service.create_album(name="", album_type="manual")


def test_update_album_name_and_description(service: AlbumService):
    album = service.create_album(name="Old Name", album_type="manual")

    updated = service.update_album(
        album_id=album.id,
        name="New Name",
        description="Updated",
    )

    assert updated is not None
    assert updated.name == "New Name"
    assert updated.description == "Updated"
    assert updated.updated_at > updated.created_at


def test_delete_album_does_not_delete_images(
    service: AlbumService,
    repository: MetadataRepository,
):
    image_hashes = _seed_images(repository, 3)
    album = service.create_album(name="Travel", album_type="manual")

    with repository.connect() as connection:
        for content_hash in image_hashes:
            connection.execute(
                """
                INSERT INTO album_images (album_id, content_hash, sort_order, added_at)
                VALUES (?, ?, ?, ?)
                """,
                (album.id, content_hash, 0, datetime.now(UTC).isoformat()),
            )

    service.delete_album(album.id)

    assert service.get_album(album.id) is None
    for content_hash in image_hashes:
        assert repository.get_image(content_hash) is not None


def test_get_nonexistent_album_returns_none(service: AlbumService):
    assert service.get_album(9999) is None


def test_add_images_to_manual_album(service: AlbumService, repository: MetadataRepository):
    image_hashes = _seed_images(repository, 3)
    album = service.create_album(name="Favorites", album_type="manual")

    added = service.add_images_to_album(album.id, image_hashes)
    refreshed = service.get_album(album.id)

    assert added == 3
    assert refreshed is not None
    assert refreshed.image_count == 3


def test_image_can_belong_to_multiple_albums(service: AlbumService, repository: MetadataRepository):
    image_hash = _seed_images(repository, 1)[0]
    album_a = service.create_album(name="Album A", album_type="manual")
    album_b = service.create_album(name="Album B", album_type="manual")

    service.add_images_to_album(album_a.id, [image_hash])
    service.add_images_to_album(album_b.id, [image_hash])

    assert [image.content_hash for image in service.list_album_images(album_a.id).items] == [image_hash]
    assert [image.content_hash for image in service.list_album_images(album_b.id).items] == [image_hash]


def test_remove_image_from_manual_album(service: AlbumService, repository: MetadataRepository):
    image_hash = _seed_images(repository, 1)[0]
    album = service.create_album(name="Manual Remove", album_type="manual")
    service.add_images_to_album(album.id, [image_hash])

    removed = service.remove_images_from_album(album.id, [image_hash])
    refreshed = service.get_album(album.id)

    assert removed == 1
    assert refreshed is not None
    assert refreshed.image_count == 0
    assert repository.get_image(image_hash) is not None


def test_cannot_add_images_to_smart_album(service: AlbumService):
    album = service.create_album(name="Auto Pets", album_type="smart", rule_logic="or")

    with pytest.raises(ValueError, match="smart album"):
        service.add_images_to_album(album.id, ["abc123"])


def test_adding_duplicate_image_is_idempotent(service: AlbumService, repository: MetadataRepository):
    image_hash = _seed_images(repository, 1)[0]
    album = service.create_album(name="Duplicate", album_type="manual")

    assert service.add_images_to_album(album.id, [image_hash]) == 1
    assert service.add_images_to_album(album.id, [image_hash]) == 0
    refreshed = service.get_album(album.id)
    assert refreshed is not None
    assert refreshed.image_count == 1


def test_bulk_add_images_to_album(service: AlbumService, repository: MetadataRepository):
    image_hashes = _seed_images(repository, 10)
    album = service.create_album(name="Batch", album_type="manual")

    added = service.add_images_to_album(album.id, image_hashes)

    assert added == 10
    assert service.get_album(album.id).image_count == 10


def test_paginate_album_images_with_cursor(service: AlbumService, repository: MetadataRepository):
    image_hashes = _seed_images(repository, 25)
    album = service.create_album(name="Large", album_type="manual")
    service.add_images_to_album(album.id, image_hashes)

    first_page = service.list_album_images(album.id, limit=10)
    second_page = service.list_album_images(album.id, limit=10, cursor=first_page.next_cursor)
    third_page = service.list_album_images(album.id, limit=10, cursor=second_page.next_cursor)

    assert len(first_page.items) == 10
    assert first_page.next_cursor is not None
    assert len(second_page.items) == 10
    assert second_page.next_cursor is not None
    assert len(third_page.items) == 5
    assert third_page.next_cursor is None


def test_cannot_remove_images_from_smart_album(service: AlbumService):
    album = service.create_album(name="Auto", album_type="smart", rule_logic="and")

    with pytest.raises(ValueError, match="smart album"):
        service.remove_images_from_album(album.id, ["abc123"])


def test_bulk_add_exceeding_limit_returns_error(service: AlbumService):
    album = service.create_album(name="Limit Test", album_type="manual")

    with pytest.raises(ValueError, match="maximum"):
        service.add_images_to_album(album.id, [f"hash-{index}" for index in range(501)])


def test_manual_album_cover_is_first_image_by_sort_order(
    service: AlbumService,
    repository: MetadataRepository,
):
    image_hashes = _seed_images(repository, 3)
    album = service.create_album(name="Travel", album_type="manual")
    service.add_images_to_album(album.id, image_hashes)

    travel = next(item for item in service.list_albums() if item.id == album.id)

    assert travel.cover_image is not None
    assert travel.cover_image.content_hash == image_hashes[0]


def test_empty_album_has_null_cover(service: AlbumService):
    album = service.create_album(name="Empty", album_type="manual")

    empty = next(item for item in service.list_albums() if item.id == album.id)

    assert empty.cover_image is None


def test_list_albums_shows_image_count_and_cover(
    service: AlbumService,
    repository: MetadataRepository,
):
    manual_hashes = _seed_images(repository, 5)
    smart_hashes = _seed_images(repository, 8)
    sunset = repository.create_tag("sunset")
    for content_hash in smart_hashes[:3]:
        repository.add_tag_to_image(content_hash, sunset.id)

    manual_album = service.create_album(name="A", album_type="manual")
    smart_album = service.create_album(name="B", album_type="smart", rule_logic="or")
    empty_album = service.create_album(name="C", album_type="manual")

    service.add_images_to_album(manual_album.id, manual_hashes)
    service.set_album_rules(
        smart_album.id,
        [{"tag_id": sunset.id, "match_mode": "include"}],
    )

    albums = {album.name: album for album in service.list_albums()}

    assert len(albums) == 3
    assert albums["A"].image_count == 5
    assert albums["A"].cover_image is not None
    assert albums["B"].image_count == 3
    assert albums["B"].cover_image is not None
    assert albums["C"].image_count == 0
    assert albums["C"].cover_image is None
