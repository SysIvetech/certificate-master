"""Unit tests for recommendation schemas (active schemas only).

비활성 RecommendationRequest/RecommendationResponse 테스트 제거 (2026-02-20).
Contextual Retrieval 전환으로 구 위자드 플로우 비활성화.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError


class TestFeasibilitySchema:
    """Test Feasibility schema validation."""

    def test_feasibility_all_fields(self):
        """Test Feasibility with all fields."""
        from app.schemas.recommendation import Feasibility

        data = {
            "can_prepare": True,
            "estimated_days": 90,
        }

        feasibility = Feasibility(**data)

        assert feasibility.can_prepare is True
        assert feasibility.estimated_days == 90

    def test_feasibility_cannot_prepare(self):
        """Test Feasibility when cannot prepare."""
        from app.schemas.recommendation import Feasibility

        data = {
            "can_prepare": False,
            "estimated_days": 365,
        }

        feasibility = Feasibility(**data)

        assert feasibility.can_prepare is False
        assert feasibility.estimated_days == 365


class TestRecommendedCertificateSchema:
    """Test RecommendedCertificate schema validation."""

    def test_recommended_certificate_all_fields(self):
        """Test RecommendedCertificate with all fields."""
        from app.schemas.recommendation import RecommendedCertificate

        cert_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "raw_id": "T_정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보기술",
            "title": "정보처리기사",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        data = {
            "certificate": cert_data,
            "qualification_category": "국가기술자격",
            "match_score": 95,
            "recommendation_reason": "데이터/IT 분야 이직 준비에 적합합니다.",
            "key_points": [
                "중급 난이도",
                "6개월 이하 준비 가능",
                "관련 직무 활용도 높음",
            ],
            "feasibility": {
                "can_prepare": True,
                "estimated_days": 90,
            },
        }

        rec = RecommendedCertificate(**data)

        assert rec.match_score == 95
        assert "이직" in rec.recommendation_reason
        assert len(rec.key_points) == 3
        assert rec.feasibility.can_prepare is True
        assert rec.feasibility.estimated_days == 90

    def test_recommended_certificate_match_score_range(self):
        """Test that match_score must be between 0 and 100."""
        from app.schemas.recommendation import RecommendedCertificate

        cert_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "raw_id": "T_정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보기술",
            "title": "정보처리기사",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        with pytest.raises(ValidationError):
            RecommendedCertificate(
                certificate=cert_data,
                qualification_category="국가기술자격",
                match_score=150,
                recommendation_reason="테스트",
                key_points=[],
                feasibility={"can_prepare": True, "estimated_days": 90},
            )

        with pytest.raises(ValidationError):
            RecommendedCertificate(
                certificate=cert_data,
                qualification_category="국가기술자격",
                match_score=-10,
                recommendation_reason="테스트",
                key_points=[],
                feasibility={"can_prepare": True, "estimated_days": 90},
            )


# ===== 통합 추천 스키마 테스트 =====


def test_unified_request_valid():
    """유효한 통합 추천 요청."""
    from app.schemas.recommendation import UnifiedRecommendationRequest

    req = UnifiedRecommendationRequest(
        domains=["IT/소프트웨어"],
        user_input="비전공자인데 3개월 안에 딸 수 있는 IT 자격증 추천해주세요",
    )
    assert req.domains == ["IT/소프트웨어"]
    assert len(req.user_input) >= 10


def test_unified_request_multiple_domains():
    """복수 도메인 선택."""
    from app.schemas.recommendation import UnifiedRecommendationRequest

    req = UnifiedRecommendationRequest(
        domains=["IT/소프트웨어", "전기/전자"],
        user_input="IT나 전기 쪽 자격증을 준비하고 싶습니다",
    )
    assert len(req.domains) == 2


def test_unified_request_empty_domains_allowed():
    """도메인이 비어있어도 허용된다 (자동 추론 모드)."""
    from app.schemas.recommendation import UnifiedRecommendationRequest

    req = UnifiedRecommendationRequest(
        domains=[],
        user_input="테스트 입력입니다 충분히 길게",
    )
    assert req.domains == []


def test_unified_request_short_input_fails():
    """user_input이 10자 미만이면 실패."""
    from app.schemas.recommendation import UnifiedRecommendationRequest

    with pytest.raises(ValidationError):
        UnifiedRecommendationRequest(
            domains=["IT/소프트웨어"],
            user_input="짧음",
        )
