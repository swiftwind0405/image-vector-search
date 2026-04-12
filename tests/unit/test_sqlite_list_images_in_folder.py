from datetime import UTC, datetime

from image_vector_search.domain.models import ImageRecord
from image_vector_search.repositories.sqlite import MetadataRepository

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_repo(tmp_path) -> MetadataRepository:
    repo = MetadataRepository(tmp_path / "test.db")
    repo.initialize_schema()
    return repo


def _make_image(
    content_hash: str,
    canonical_path: str,
    *,
    is_active: bool = True,
) -> ImageRecord:
    return ImageRecord(
        content_hash=content_hash,
        canonical_path=canonical_path,
        file_size=1000,
        mtime=1000.0,
        mime_type="image/jpeg",
        width=100,
        height=100,
        is_active=is_active,
        last_seen_at=NOW,
        embedding_provider="jina",
        embedding_model="jina-clip-v2",
        embedding_version="v2",
        created_at=NOW,
        updated_at=NOW,
    )


def _insert_image(
    repo: MetadataRepository,
    content_hash: str,
    canonical_path: str,
    *,
    is_active: bool = True,
) -> None:
    repo.upsert_image(
        _make_image(content_hash, canonical_path, is_active=is_active)
    )


def test_list_images_in_folder_excludes_nested_images(tmp_path):
    repo = _make_repo(tmp_path)
    images_root = str(tmp_path / "ix")
    _insert_image(repo, "h1", f"{images_root}/a/1.jpg")
    _insert_image(repo, "h2", f"{images_root}/a/b/2.jpg")

    result = repo.list_images_in_folder(path="a", images_root=images_root)

    assert {image.canonical_path for image in result} == {f"{images_root}/a/1.jpg"}


def test_list_images_in_folder_returns_root_level_images_only(tmp_path):
    repo = _make_repo(tmp_path)
    images_root = str(tmp_path / "ix")
    _insert_image(repo, "h1", f"{images_root}/top.jpg")
    _insert_image(repo, "h2", f"{images_root}/a/1.jpg")

    result = repo.list_images_in_folder(path="", images_root=images_root)

    assert {image.canonical_path for image in result} == {f"{images_root}/top.jpg"}


def test_list_images_in_folder_excludes_inactive_images(tmp_path):
    repo = _make_repo(tmp_path)
    images_root = str(tmp_path / "ix")
    _insert_image(repo, "h1", f"{images_root}/a/1.jpg", is_active=False)

    result = repo.list_images_in_folder(path="a", images_root=images_root)

    assert result == []


def test_list_images_in_folder_paginates_stably_without_duplicates(tmp_path):
    repo = _make_repo(tmp_path)
    images_root = str(tmp_path / "ix")
    expected_paths = []
    for index in range(50):
        path = f"{images_root}/a/{index:02d}.jpg"
        expected_paths.append(path)
        _insert_image(repo, f"h{index:02d}", path)

    first_page = repo.list_images_in_folder(path="a", images_root=images_root, limit=20)
    second_page = repo.list_images_in_folder(
        path="a",
        images_root=images_root,
        limit=20,
        cursor=first_page[-1].canonical_path,
    )
    third_page = repo.list_images_in_folder(
        path="a",
        images_root=images_root,
        limit=20,
        cursor=second_page[-1].canonical_path,
    )

    combined_paths = [image.canonical_path for image in first_page + second_page + third_page]

    assert combined_paths == expected_paths
    assert len(combined_paths) == len(set(combined_paths)) == 50


def test_list_images_in_folder_returns_empty_for_non_matching_folder(tmp_path):
    repo = _make_repo(tmp_path)
    images_root = str(tmp_path / "ix")
    _insert_image(repo, "h1", f"{images_root}/z/1.jpg")

    result = repo.list_images_in_folder(path="a", images_root=images_root)

    assert result == []
