from image_search_mcp.domain.models import SearchFilters, SearchResult


def test_search_filters_normalizes_folder() -> None:
    filters = SearchFilters(folder="/data/images/2024", top_k=3, min_score=0.2)
    assert filters.folder == "/data/images/2024"
    assert filters.top_k == 3
    assert filters.min_score == 0.2


def test_search_result_serialization() -> None:
    result = SearchResult(
        content_hash="abc",
        path="/data/images/a.jpg",
        score=0.9,
        width=100,
        height=80,
        mime_type="image/jpeg",
    )
    assert result.model_dump()["content_hash"] == "abc"
