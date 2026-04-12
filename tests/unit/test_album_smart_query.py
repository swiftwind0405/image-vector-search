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


def _seed_image(repository: MetadataRepository, content_hash: str, canonical_path: str) -> None:
    repository.upsert_image(_build_image(content_hash=content_hash, canonical_path=canonical_path))


def _seed_tagged_image(
    repository: MetadataRepository,
    tags: dict[str, int],
    content_hash: str,
    canonical_path: str,
    tag_names: list[str],
) -> None:
    _seed_image(repository, content_hash, canonical_path)
    for tag_name in tag_names:
        repository.add_tag_to_image(content_hash, tags[tag_name])


def _create_tags(repository: MetadataRepository, names: list[str]) -> dict[str, int]:
    return {name: repository.create_tag(name).id for name in names}


def test_and_logic_requires_all_included_tags(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["sunset", "beach"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["sunset", "beach"])
    _seed_tagged_image(repository, tags, "img2", "/data/images/b.jpg", ["sunset"])
    _seed_tagged_image(repository, tags, "img3", "/data/images/c.jpg", ["beach"])
    album = service.create_album(name="Beach Sunsets", album_type="smart", rule_logic="and")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["sunset"], "match_mode": "include"},
            {"tag_id": tags["beach"], "match_mode": "include"},
        ],
    )

    images = service.list_album_images(album.id).items

    assert [image.content_hash for image in images] == ["img1"]


def test_or_logic_matches_any_included_tag(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["cat", "dog", "mountain"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["cat"])
    _seed_tagged_image(repository, tags, "img2", "/data/images/b.jpg", ["dog"])
    _seed_tagged_image(repository, tags, "img3", "/data/images/c.jpg", ["mountain"])
    album = service.create_album(name="Pets", album_type="smart", rule_logic="or")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["cat"], "match_mode": "include"},
            {"tag_id": tags["dog"], "match_mode": "include"},
        ],
    )

    assert {image.content_hash for image in service.list_album_images(album.id).items} == {"img1", "img2"}


def test_exclude_tag_filters_out_matching_images(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["landscape", "urban"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["landscape"])
    _seed_tagged_image(repository, tags, "img2", "/data/images/b.jpg", ["landscape", "urban"])
    album = service.create_album(name="Land", album_type="smart", rule_logic="or")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["landscape"], "match_mode": "include"},
            {"tag_id": tags["urban"], "match_mode": "exclude"},
        ],
    )

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img1"]


def test_and_with_exclude(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["food", "dessert", "savory"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["food", "dessert"])
    _seed_tagged_image(repository, tags, "img2", "/data/images/b.jpg", ["food", "savory"])
    _seed_tagged_image(repository, tags, "img3", "/data/images/c.jpg", ["food", "dessert", "savory"])
    album = service.create_album(name="Dessert", album_type="smart", rule_logic="and")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["food"], "match_mode": "include"},
            {"tag_id": tags["dessert"], "match_mode": "include"},
            {"tag_id": tags["savory"], "match_mode": "exclude"},
        ],
    )

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img1"]


def test_rule_changes_are_immediately_reflected(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["sunset", "beach"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["sunset"])
    album = service.create_album(name="Dynamic", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tags["sunset"], "match_mode": "include"}])

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img1"]

    repository.add_tag_to_image("img1", tags["beach"])
    service.set_album_rules(album.id, [{"tag_id": tags["beach"], "match_mode": "include"}])

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img1"]


def test_deleting_tag_updates_smart_album_results(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["sunset", "beach"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["sunset", "beach"])
    album = service.create_album(name="Cascade", album_type="smart", rule_logic="and")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["sunset"], "match_mode": "include"},
            {"tag_id": tags["beach"], "match_mode": "include"},
        ],
    )

    repository.delete_tag(tags["sunset"])

    rules = service.get_album_rules(album.id)
    images = service.list_album_images(album.id).items

    assert len(rules) == 1
    assert rules[0].tag_id == tags["beach"]
    assert [image.content_hash for image in images] == ["img1"]


def test_smart_album_with_no_rules_returns_no_images(service: AlbumService):
    album = service.create_album(name="Empty Rules", album_type="smart", rule_logic="or")
    assert service.list_album_images(album.id).items == []


def test_smart_album_with_no_include_rules_returns_no_images(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["landscape", "urban"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["landscape"])
    album = service.create_album(name="Exclude Only", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tags["urban"], "match_mode": "exclude"}])

    assert service.list_album_images(album.id).items == []


def test_after_all_include_tags_deleted_returns_no_images(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["sunset"])
    _seed_tagged_image(repository, tags, "img1", "/data/images/a.jpg", ["sunset"])
    album = service.create_album(name="Vanished", album_type="smart", rule_logic="and")
    service.set_album_rules(album.id, [{"tag_id": tags["sunset"], "match_mode": "include"}])

    repository.delete_tag(tags["sunset"])

    assert service.get_album_rules(album.id) == []
    assert service.list_album_images(album.id).items == []


def test_set_album_rules_with_empty_list_clears_all_rules(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["one", "two", "three"])
    album = service.create_album(name="Dynamic 2", album_type="smart", rule_logic="or")
    service.set_album_rules(
        album.id,
        [
            {"tag_id": tags["one"], "match_mode": "include"},
            {"tag_id": tags["two"], "match_mode": "include"},
            {"tag_id": tags["three"], "match_mode": "exclude"},
        ],
    )

    service.set_album_rules(album.id, [])

    assert service.get_album_rules(album.id) == []
    assert service.list_album_images(album.id).items == []


def test_set_album_rules_with_duplicate_tag_id_fails(service: AlbumService, repository: MetadataRepository):
    tag_id = repository.create_tag("sunset").id
    album = service.create_album(name="Test", album_type="smart", rule_logic="or")

    with pytest.raises(ValueError, match="Duplicate"):
        service.set_album_rules(
            album.id,
            [
                {"tag_id": tag_id, "match_mode": "include"},
                {"tag_id": tag_id, "match_mode": "exclude"},
            ],
        )


def test_paginate_smart_album_images_with_cursor(service: AlbumService, repository: MetadataRepository):
    tag_id = repository.create_tag("nature").id
    for index in range(25):
        content_hash = f"img-{index:02d}"
        _seed_image(repository, content_hash, f"/data/images/{index:02d}.jpg")
        repository.add_tag_to_image(content_hash, tag_id)
    album = service.create_album(name="Nature", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tag_id, "match_mode": "include"}])

    first_page = service.list_album_images(album.id, limit=10)
    second_page = service.list_album_images(album.id, limit=10, cursor=first_page.next_cursor)
    third_page = service.list_album_images(album.id, limit=10, cursor=second_page.next_cursor)

    assert len(first_page.items) == 10
    assert len(second_page.items) == 10
    assert len(third_page.items) == 5
    assert third_page.next_cursor is None


def test_smart_album_source_paths_only_matches_images_in_those_paths(
    service: AlbumService,
    repository: MetadataRepository,
):
    tags = _create_tags(repository, ["sunset"])
    _seed_tagged_image(repository, tags, "img1", "/tmp/root/photos/2025/sunset.jpg", ["sunset"])
    _seed_tagged_image(repository, tags, "img2", "/tmp/root/photos/2024/sunset.jpg", ["sunset"])
    _seed_tagged_image(repository, tags, "img3", "/tmp/root/videos/sunset.jpg", ["sunset"])
    album = service.create_album(name="2025", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tags["sunset"], "match_mode": "include"}])
    service.set_album_source_paths(album.id, ["photos/2025"])

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img1"]


def test_smart_album_with_multiple_source_paths(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["landscape"])
    _seed_tagged_image(repository, tags, "img1", "/tmp/root/photos/2025/land.jpg", ["landscape"])
    _seed_tagged_image(repository, tags, "img2", "/tmp/root/photos/2024/land.jpg", ["landscape"])
    _seed_tagged_image(repository, tags, "img3", "/tmp/root/other/land.jpg", ["landscape"])
    album = service.create_album(name="Paths", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tags["landscape"], "match_mode": "include"}])
    service.set_album_source_paths(album.id, ["photos/2025", "photos/2024"])

    assert {image.content_hash for image in service.list_album_images(album.id).items} == {"img1", "img2"}


def test_smart_album_with_no_source_paths_matches_all_images(service: AlbumService, repository: MetadataRepository):
    tags = _create_tags(repository, ["nature"])
    _seed_tagged_image(repository, tags, "img1", "/tmp/root/photos/2025/a.jpg", ["nature"])
    _seed_tagged_image(repository, tags, "img2", "/tmp/root/other/b.jpg", ["nature"])
    album = service.create_album(name="All", album_type="smart", rule_logic="or")
    service.set_album_rules(album.id, [{"tag_id": tags["nature"], "match_mode": "include"}])

    assert [image.content_hash for image in service.list_album_images(album.id).items] == ["img2", "img1"] or [image.content_hash for image in service.list_album_images(album.id).items] == ["img1", "img2"]


def test_set_source_paths_for_smart_album(service: AlbumService):
    album = service.create_album(name="Travel", album_type="smart", rule_logic="or")

    service.set_album_source_paths(album.id, ["photos/travel", "photos/vacation"])

    assert service.get_album_source_paths(album.id) == ["photos/travel", "photos/vacation"]


def test_cannot_set_source_paths_for_manual_album(service: AlbumService):
    album = service.create_album(name="Manual", album_type="manual")

    with pytest.raises(ValueError, match="manual album"):
        service.set_album_source_paths(album.id, ["photos/travel"])
