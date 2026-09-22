"""리랭킹 통합 테스트.

추천 서비스에서 리랭킹이 제대로 작동하는지 검증합니다.
"""

from unittest.mock import MagicMock

from app.schemas.recommendation import StructuredUserContext
from app.services.study.natural_recommendation_service import (
    NaturalRecommendationService,
)


class TestRerankingIntegration:
    """리랭킹 통합 테스트."""

    def test_extract_user_domains_from_it_context(self):
        """IT 관련 컨텍스트에서 도메인을 올바르게 추출해야 함."""
        service = NaturalRecommendationService(db=None)

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT", "소프트웨어"],
        )

        domains = service._extract_user_domains(context)

        assert "IT개발" in domains

    def test_extract_user_domains_from_finance_context(self):
        """금융 관련 컨텍스트에서 도메인을 올바르게 추출해야 함."""
        service = NaturalRecommendationService(db=None)

        context = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=180,
            difficulty_preference="중",
            preferred_industries=["금융", "회계"],
        )

        domains = service._extract_user_domains(context)

        assert "금융" in domains

    def test_calculate_rerank_boost_for_it_certificate(self):
        """IT 자격증에 대해 부스팅 점수를 계산해야 함."""
        service = NaturalRecommendationService(db=None)

        # IT 자격증
        it_cert = {
            "id": "1",
            "title": "정보처리기사",
            "series": "기사",
            "difficulty": 3,
            "study_period_days": 90,
            "career_info": {"industry": ["IT", "정보처리"]},
        }

        boost = service._calculate_rerank_boost(
            cert=it_cert,
            similarity=0.40,
            user_domains=["IT개발"],
        )

        # IT 키워드 부스팅(0.15) + 산업 매칭(0.10) = +0.25
        assert boost > 0.20  # 부스팅이 충분히 적용되었는지

    def test_calculate_rerank_boost_penalizes_excluded_keywords(self):
        """제외 키워드가 있는 자격증은 감점되어야 함."""
        service = NaturalRecommendationService(db=None)

        # 건설 자격증
        construction_cert = {
            "id": "2",
            "title": "전산응용건축제도기능사",
            "series": "기능사",
            "difficulty": 2,
            "study_period_days": 60,
            "career_info": {"industry": ["건설", "건축"]},
        }

        boost = service._calculate_rerank_boost(
            cert=construction_cert,
            similarity=0.45,
            user_domains=["IT개발"],
        )

        # 제외 키워드 패널티(-0.20)로 음수 부스트
        assert boost < 0

    def test_reranking_changes_final_scores(self):
        """리랭킹이 최종 점수를 변경해야 함."""
        service = NaturalRecommendationService(db=None)
        service._calculate_final_score = MagicMock(return_value=50)  # 기본 점수 고정

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )

        # IT 자격증
        it_cert = {
            "id": "1",
            "title": "정보처리기사",
            "series": "기사",
            "difficulty": 3,
            "study_period_days": 90,
            "career_info": {"industry": ["IT"]},
        }

        # 제조 자격증
        manufacturing_cert = {
            "id": "2",
            "title": "제품응용모델링산업기사",
            "series": "산업기사",
            "difficulty": 3,
            "study_period_days": 90,
            "career_info": {"industry": ["제조", "CAD"]},
        }

        user_domains = service._extract_user_domains(context)

        # IT 자격증 리랭킹 부스트
        it_boost = service._calculate_rerank_boost(it_cert, 0.40, user_domains)

        # 제조 자격증 리랭킹 부스트
        manufacturing_boost = service._calculate_rerank_boost(
            manufacturing_cert, 0.45, user_domains
        )

        # IT 자격증의 부스트가 제조 자격증보다 훨씬 높아야 함
        assert it_boost > manufacturing_boost + 0.20
