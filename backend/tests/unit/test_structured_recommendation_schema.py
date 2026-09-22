"""구조화된 추천 요청 스키마 테스트."""

import pytest
from pydantic import ValidationError

from app.schemas.recommendation import StructuredRecommendationRequest


class TestStructuredRecommendationRequest:

    def test_valid_minimal_request(self):
        req = StructuredRecommendationRequest(
            domains=["IT개발"],
            purpose="취업",
            current_status="학생",
        )
        assert req.domains == ["IT개발"]
        assert req.purpose == "취업"
        assert req.preference_tags == []
        assert req.additional_input == ""

    def test_valid_full_request(self):
        req = StructuredRecommendationRequest(
            domains=["IT개발", "데이터"],
            purpose="이직",
            current_status="직장인",
            preference_tags=["독학 가능", "비전공자"],
            additional_input="데이터 분석 관심",
        )
        assert len(req.domains) == 2
        assert len(req.preference_tags) == 2

    def test_domains_required(self):
        with pytest.raises(ValidationError):
            StructuredRecommendationRequest(
                purpose="취업",
                current_status="학생",
            )

    def test_purpose_required(self):
        with pytest.raises(ValidationError):
            StructuredRecommendationRequest(
                domains=["IT개발"],
                current_status="학생",
            )

    def test_empty_domains_rejected(self):
        with pytest.raises(ValidationError):
            StructuredRecommendationRequest(
                domains=[],
                purpose="취업",
                current_status="학생",
            )
