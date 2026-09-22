"""SearchStats 스키마 테스트."""

from app.schemas.recommendation import SearchStats, UnifiedRecommendationResponse


class TestSearchStats:
    def test_creates_with_valid_data(self):
        stats = SearchStats(
            dense_count=20, sparse_count=15, merged_count=10, elapsed_ms=123.45
        )
        assert stats.dense_count == 20
        assert stats.sparse_count == 15
        assert stats.merged_count == 10
        assert stats.elapsed_ms == 123.45

    def test_serializes_to_dict(self):
        stats = SearchStats(
            dense_count=5, sparse_count=3, merged_count=5, elapsed_ms=50.0
        )
        d = stats.model_dump()
        assert "dense_count" in d
        assert "sparse_count" in d
        assert "merged_count" in d
        assert "elapsed_ms" in d


class TestUnifiedResponseIncludesSearchStats:
    def test_has_search_stats_field(self):
        fields = UnifiedRecommendationResponse.model_fields
        assert "search_stats" in fields
