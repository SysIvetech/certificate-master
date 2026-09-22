"""구조화된 쿼리 생성 함수 테스트."""

from app.services.search.structured_query import (
    build_structured_metadata_filter,
    build_structured_query,
)


class TestBuildStructuredQuery:

    def test_includes_domain(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
        )
        assert "IT개발" in result

    def test_includes_target_for_student(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
        )
        assert "비전공자" in result or "입문자" in result

    def test_includes_purpose(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="이직",
            current_status="직장인",
        )
        assert "이직" in result

    def test_includes_target_for_worker(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="이직",
            current_status="직장인",
        )
        assert "직장인" in result or "경력자" in result

    def test_preference_tags_appended(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
            preference_tags=["독학 가능", "비전공자"],
        )
        assert "독학" in result
        assert "비전공자" in result

    def test_additional_input_appended(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
            additional_input="데이터 분석에 관심",
        )
        assert "데이터 분석" in result

    def test_multiple_domains(self):
        result = build_structured_query(
            domains=["IT개발", "데이터"],
            purpose="취업",
            current_status="학생",
        )
        assert "IT개발" in result
        assert "데이터" in result

    def test_empty_preference_tags(self):
        result = build_structured_query(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
            preference_tags=[],
        )
        assert isinstance(result, str)
        assert len(result) > 0


class TestBuildStructuredMetadataFilter:

    def test_returns_none_when_no_preferences(self):
        result = build_structured_metadata_filter(
            preference_tags=[],
            current_status="학생",
        )
        assert result is None

    def test_non_major_filter(self):
        result = build_structured_metadata_filter(
            preference_tags=["독학 가능"],
            current_status="학생",
        )
        assert result == {"non_major_friendly": True}

    def test_bijeongong_filter(self):
        result = build_structured_metadata_filter(
            preference_tags=["비전공자"],
            current_status="학생",
        )
        assert result == {"non_major_friendly": True}

    def test_cbt_filter(self):
        result = build_structured_metadata_filter(
            preference_tags=["CBT 상시시험"],
            current_status="학생",
        )
        assert result == {"cbt_available": True}

    def test_combined_filters(self):
        result = build_structured_metadata_filter(
            preference_tags=["독학 가능", "CBT 상시시험"],
            current_status="학생",
        )
        assert result is not None
        assert "$and" in result
        assert len(result["$and"]) == 2

    def test_none_preference_tags(self):
        result = build_structured_metadata_filter(
            preference_tags=None,
            current_status="학생",
        )
        assert result is None
