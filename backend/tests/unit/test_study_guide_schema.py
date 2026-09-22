"""Unit tests for study_guide schema.

Tests the StudyGuide Pydantic model structure and validation.
"""

from app.schemas.certificate import (
    RecommendedBook,
    StudyGuide,
    TimeAllocation,
)


class TestStudyGuideSchema:
    """Test StudyGuide schema validation."""

    def test_study_guide_all_fields(self):
        """Test StudyGuide with all fields populated."""
        data = {
            "study_methods": [
                "교재 중심 학습",
                "기출문제 위주",
                "강의 + 문제풀이 병행",
            ],
            "time_allocation": {"theory": "40%", "practice": "50%", "review": "10%"},
            "recommended_books": [
                {
                    "title": "정보처리기사 필기 교재",
                    "publisher": "시대에듀",
                    "type": "필기",
                    "description": "기본서로 추천",
                }
            ],
            "success_tips": ["기출문제 최소 3회 반복", "오답노트 필수 작성"],
        }

        guide = StudyGuide(**data)

        assert len(guide.study_methods) == 3
        assert "교재 중심 학습" in guide.study_methods
        assert guide.time_allocation["theory"] == "40%"
        assert guide.time_allocation["practice"] == "50%"
        assert len(guide.recommended_books) == 1
        assert guide.recommended_books[0]["title"] == "정보처리기사 필기 교재"
        assert len(guide.success_tips) == 2

    def test_study_guide_minimal_fields(self):
        """Test StudyGuide with only required fields (defaults)."""
        data = {}

        guide = StudyGuide(**data)

        assert guide.study_methods == []
        assert guide.time_allocation is None
        assert guide.recommended_books == []
        assert guide.success_tips == []

    def test_time_allocation_schema(self):
        """Test TimeAllocation sub-schema."""
        data = {"theory": "40%", "practice": "50%", "review": "10%"}

        allocation = TimeAllocation(**data)

        assert allocation.theory == "40%"
        assert allocation.practice == "50%"
        assert allocation.review == "10%"

    def test_time_allocation_optional_fields(self):
        """Test TimeAllocation with optional fields."""
        data = {"theory": "50%", "practice": "50%"}

        allocation = TimeAllocation(**data)

        assert allocation.theory == "50%"
        assert allocation.practice == "50%"
        assert allocation.review is None

    def test_recommended_book_schema(self):
        """Test RecommendedBook sub-schema."""
        data = {
            "title": "정보처리기사 필기",
            "publisher": "시대에듀",
            "type": "필기",
            "description": "기본서로 추천",
        }

        book = RecommendedBook(**data)

        assert book.title == "정보처리기사 필기"
        assert book.publisher == "시대에듀"
        assert book.type == "필기"
        assert book.description == "기본서로 추천"

    def test_recommended_book_minimal_fields(self):
        """Test RecommendedBook with only required fields."""
        data = {
            "title": "정보처리기사 필기",
        }

        book = RecommendedBook(**data)

        assert book.title == "정보처리기사 필기"
        assert book.publisher is None
        assert book.type is None
        assert book.description is None

    def test_study_guide_with_empty_time_allocation(self):
        """Test study_guide with null time_allocation."""
        data = {"study_methods": ["교재 중심"], "time_allocation": None}

        guide = StudyGuide(**data)

        assert guide.study_methods == ["교재 중심"]
        assert guide.time_allocation is None

    def test_study_guide_in_certificate_update(self):
        """Test study_guide field in CertificateUpdate schema."""
        from app.schemas.certificate import CertificateUpdate

        data = {
            "study_guide": {
                "study_methods": ["교재 중심"],
                "learning_sequence": ["1단계: 기초 (30일)"],
                "success_tips": ["기출문제 반복"],
            }
        }

        update = CertificateUpdate(**data)

        assert update.study_guide is not None
        assert update.study_guide["study_methods"] == ["교재 중심"]

    def test_study_guide_in_certificate_response(self):
        """Test study_guide field in Certificate response schema."""
        from datetime import datetime

        from app.schemas.certificate import Certificate

        data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "raw_id": "T_정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보기술",
            "title": "정보처리기사",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "study_guide": {
                "study_methods": ["교재 + 기출"],
                "learning_sequence": ["1단계: 기초"],
                "success_tips": ["반복 학습"],
            },
        }

        cert = Certificate(**data)

        assert cert.study_guide is not None
        assert cert.study_guide["study_methods"] == ["교재 + 기출"]
