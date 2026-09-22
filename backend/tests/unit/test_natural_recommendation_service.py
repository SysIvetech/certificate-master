"""리디자인된 추천 서비스 테스트."""

from app.schemas.recommendation import StructuredUserContext
from app.services.study.natural_recommendation_service import (
    NaturalRecommendationService,
)


def _make_context(**overrides) -> StructuredUserContext:
    """테스트용 StructuredUserContext를 생성합니다."""
    defaults = {
        "goal": "취업",
        "employment_status": "학생",
        "major_background": "비전공자",
        "weekly_study_hours": 10,
        "max_study_period_days": 90,
        "difficulty_preference": "중",
        "preferred_industries": ["IT"],
    }
    defaults.update(overrides)
    return StructuredUserContext(**defaults)


def test_calculate_score_high_similarity():
    """유사도가 높으면 점수가 높다."""
    service = NaturalRecommendationService(db=None)
    context = _make_context()

    cert = {
        "feasibility_info": {"self_study_possible": True},
        "study_period_days": 60,
        "job_market_info": {"job_posting_frequency": "많음"},
    }

    score = service._calculate_score(0.8, cert, context)
    # 0.8 * 70 = 56 + 10 (비전공자) + 10 (채용시장) = 76
    assert score >= 70


def test_calculate_score_non_major_penalty():
    """비전공자인데 독학 불가면 감점."""
    service = NaturalRecommendationService(db=None)
    context = _make_context()

    cert = {
        "feasibility_info": {"self_study_possible": False},
        "study_period_days": 60,
        "job_market_info": {},
    }

    score = service._calculate_score(0.5, cert, context)
    # 0.5 * 70 = 35 - 15 (감점) = 20
    assert score <= 25


def test_calculate_score_non_major_null_neutral():
    """비전공자인데 독학 정보 없으면 중립."""
    service = NaturalRecommendationService(db=None)
    context = _make_context()

    cert = {
        "feasibility_info": {},
        "study_period_days": 60,
        "job_market_info": {},
    }

    score = service._calculate_score(0.5, cert, context)
    # self_study_possible가 None이면 중립 (보너스도 감점도 없음)
    # 0.5 * 70 = 35
    assert 30 <= score <= 40


def test_calculate_score_working_adult_bonus():
    """재직자이면 준비 기간에 따른 보너스."""
    service = NaturalRecommendationService(db=None)
    context = _make_context(employment_status="재직 중", max_study_period_days=180)

    cert = {
        "feasibility_info": {},
        "study_period_days": 60,  # 180 * 0.7 = 126 이하이므로 +10
        "job_market_info": {},
    }

    score = service._calculate_score(0.5, cert, context)
    # 0.5 * 70 = 35 + 10 (재직자 보너스) = 45
    assert 40 <= score <= 50


def test_calculate_score_capped_at_100():
    """점수가 100을 초과하지 않는다."""
    service = NaturalRecommendationService(db=None)
    context = _make_context(employment_status="재직 중", max_study_period_days=180)

    cert = {
        "feasibility_info": {"self_study_possible": True},
        "study_period_days": 60,
        "job_market_info": {"job_posting_frequency": "매우 많음"},
    }

    score = service._calculate_score(1.0, cert, context)
    # 1.0 * 70 = 70 + 10 (비전공자) + 10 (재직자) + 10 (채용시장) = 100
    assert score <= 100
