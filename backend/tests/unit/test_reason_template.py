"""데이터 기반 동적 템플릿 이유 생성 테스트."""

import pytest

from app.schemas.recommendation import StructuredUserContext
from app.services.search.reason_template import ReasonTemplateEngine


@pytest.fixture
def engine():
    return ReasonTemplateEngine()


@pytest.fixture
def context_employment():
    return StructuredUserContext(
        goal="취업",
        employment_status="구직 중",
        major_background="비전공자",
        weekly_study_hours=15,
        max_study_period_days=90,
        difficulty_preference="중",
        preferred_industries=["IT"],
    )


@pytest.fixture
def context_career():
    return StructuredUserContext(
        goal="전문성 강화",
        employment_status="재직 중",
        major_background="전공자",
        weekly_study_hours=10,
        max_study_period_days=180,
        difficulty_preference="상",
        preferred_industries=["건설"],
    )


@pytest.fixture
def cert_with_job_market():
    return {
        "title": "정보처리기사",
        "career_info": {
            "industry": "IT/소프트웨어",
            "related_jobs": "소프트웨어 개발자, 시스템 엔지니어",
            "use_cases": "시스템 설계, 데이터베이스 관리",
        },
        "job_market_info": {
            "job_posting_frequency": "많음",
            "preferred_industries": "IT, 금융, 제조",
            "preferred_companies": "삼성SDS, LG CNS",
            "requirement_type": "우대",
            "salary_premium": "약 10% 상승",
        },
        "feasibility_info": {
            "self_study_possible": True,
            "non_major_pass_rate": "35%",
            "minimum_study_period": "3개월",
        },
        "study_period_days": 90,
        "difficulty": 3,
        "exam_info": {"passing_rate": "30%"},
        "cost_info": {"exam_fee": "19400원"},
        "public_sector_info": {"points": "2점"},
    }


@pytest.fixture
def cert_minimal():
    return {
        "title": "테스트자격증",
        "career_info": {},
        "job_market_info": {},
        "feasibility_info": {},
        "study_period_days": 60,
        "difficulty": 2,
    }


class TestReasonTemplateEngine:
    def test_generates_non_empty_reason(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        assert len(reason) > 0
        assert isinstance(reason, str)

    def test_reason_contains_cert_specific_data(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        has_specific = any(
            keyword in reason
            for keyword in ["IT", "소프트웨어", "정보처리", "삼성", "LG", "개발"]
        )
        assert has_specific, f"Reason lacks specific data: {reason}"

    def test_reason_adapts_to_employment_goal(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        employment_keywords = ["채용", "취업", "우대", "기업", "공고", "경쟁력"]
        has_employment = any(k in reason for k in employment_keywords)
        assert has_employment, f"Employment goal not reflected: {reason}"

    def test_reason_adapts_to_career_goal(
        self, engine, cert_with_job_market, context_career
    ):
        reason = engine.generate(cert_with_job_market, context_career)
        career_keywords = ["전문", "경력", "연봉", "상승", "프리미엄", "역량"]
        has_career = any(k in reason for k in career_keywords)
        assert has_career, f"Career goal not reflected: {reason}"

    def test_reason_for_non_major(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        non_major_keywords = ["독학", "비전공", "가능", "접근", "합격"]
        has_non_major = any(k in reason for k in non_major_keywords)
        assert has_non_major, f"Non-major context not reflected: {reason}"

    def test_minimal_cert_still_generates_reason(
        self, engine, cert_minimal, context_employment
    ):
        reason = engine.generate(cert_minimal, context_employment)
        assert len(reason) > 10

    def test_reason_has_multiple_sentences(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        sentences = [s.strip() for s in reason.split(".") if s.strip()]
        assert len(sentences) >= 2, f"Too few sentences: {reason}"

    def test_reason_length_reasonable(
        self, engine, cert_with_job_market, context_employment
    ):
        reason = engine.generate(cert_with_job_market, context_employment)
        assert 50 <= len(reason) <= 300, f"Reason length {len(reason)}: {reason}"
