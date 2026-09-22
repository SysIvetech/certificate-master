"""certificate_formatter 임베딩 보강 테스트.

사용자 추천 매칭을 위한 임베딩 텍스트 보강 기능 테스트.
"""

import pytest

from app.utils.certificate_formatter import (
    build_user_matching_metadata,  # NEW: 사용자 매칭용 메타데이터
    format_certificate_text,
    format_user_matching_text,  # NEW: 사용자 매칭용 텍스트
)

# ============================================================
# 테스트 픽스처: 보강된 자격증 데이터
# ============================================================


@pytest.fixture
def enriched_certificate():
    """보강된 자격증 데이터 픽스처."""
    return {
        "id": "test-cert-001",
        "title": "정보처리기사",
        "categories": [{"code": "IT", "name": "IT/컴퓨터"}],
        "series": "정보처리",
        "overview": "IT 분야의 대표적인 국가기술자격증입니다.",
        "difficulty": 3,
        "study_period_days": 90,
        # 진로 정보
        "career_info": {
            "industry": ["IT", "금융", "제조"],
            "use_cases": ["시스템 개발", "DB 관리", "IT 컨설팅"],
            "related_jobs": ["개발자", "IT 컨설턴트", "시스템 분석가"],
            "job_prospects": "IT 산업 성장과 함께 수요 지속 증가",
            "average_salary": "4,500만원",
        },
        # 채용 시장 정보
        "job_market_info": {
            "job_posting_frequency": "매우 높음",
            "preferred_industries": ["IT/소프트웨어", "금융/은행", "공공기관"],
            "preferred_companies": ["삼성SDS", "LG CNS", "NHN", "카카오"],
            "requirement_type": "우대",
            "public_sector_points": "공무원 가산점 3-5%",
            "salary_premium": "약 10-15% 연봉 상승 효과",
        },
        # 비용 정보
        "cost_breakdown": {
            "exam_fee": "필기 19,400원, 실기 22,600원",
            "total_estimated_cost": "30-50만원 (교재+인강 포함)",
            "free_resources": ["큐넷 기출문제", "유튜브 강의", "카페 자료"],
        },
        # 합격 가능성 정보
        "feasibility_info": {
            "non_major_pass_rate": "40-50%",
            "self_study_possible": True,
            "minimum_study_period": 60,
            "working_adult_tips": [
                "출퇴근 시간 활용",
                "주말 집중 학습",
                "기출문제 반복",
            ],
        },
        # 시험 일정 정보
        "exam_schedule_detail": {
            "cbt_available": False,
            "annual_exam_count": 3,
        },
        # 시험 정보
        "exam_info": {
            "exam_type": "필기+실기",
            "subjects": ["소프트웨어 설계", "데이터베이스", "운영체제"],
        },
    }


# ============================================================
# 사용자 매칭용 텍스트 생성 테스트
# ============================================================


class TestFormatUserMatchingText:
    """사용자 매칭용 임베딩 텍스트 생성 테스트."""

    def test_includes_target_audience_section(self, enriched_certificate):
        """추천 대상 섹션이 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        assert "[추천 대상]" in result

    def test_includes_non_major_recommendation(self, enriched_certificate):
        """비전공자 추천 여부가 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 비전공자 관련 텍스트가 있어야 함
        assert "비전공자" in result

    def test_includes_working_adult_recommendation(self, enriched_certificate):
        """직장인 추천 여부가 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 직장인 관련 텍스트가 있어야 함
        assert "직장인" in result

    def test_includes_budget_range(self, enriched_certificate):
        """예산 범위가 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 비용/예산 관련 텍스트가 있어야 함
        assert "예산" in result or "비용" in result

    def test_includes_study_time_requirement(self, enriched_certificate):
        """학습 시간 요구량이 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 학습 시간 관련 텍스트가 있어야 함
        assert "학습 시간" in result or "공부 시간" in result

    def test_includes_exam_format_summary(self, enriched_certificate):
        """시험 형태 요약이 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 시험 형태 관련 텍스트가 있어야 함
        assert "시험 형태" in result or "CBT" in result

    def test_includes_target_job_section(self, enriched_certificate):
        """목표 직종 섹션이 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        assert "[목표 직종]" in result

    def test_includes_target_company_type(self, enriched_certificate):
        """희망 기업 유형이 포함되는지 확인."""
        result = format_user_matching_text(enriched_certificate)

        # 기업 유형 관련 텍스트가 있어야 함
        assert "기업" in result or "회사" in result


# ============================================================
# 사용자 매칭용 메타데이터 테스트
# ============================================================


class TestBuildUserMatchingMetadata:
    """사용자 매칭용 메타데이터 생성 테스트."""

    def test_includes_non_major_friendly(self, enriched_certificate):
        """비전공자 친화도 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "non_major_friendly" in result
        assert isinstance(result["non_major_friendly"], bool)

    def test_includes_working_adult_friendly(self, enriched_certificate):
        """직장인 친화도 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "working_adult_friendly" in result
        assert isinstance(result["working_adult_friendly"], bool)

    def test_includes_budget_category(self, enriched_certificate):
        """예산 범주 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "budget_category" in result
        # low, medium, high 중 하나
        assert result["budget_category"] in ["low", "medium", "high"]

    def test_includes_weekly_hours_required(self, enriched_certificate):
        """주당 필요 학습시간 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "weekly_hours_required" in result
        assert isinstance(result["weekly_hours_required"], (int, float))

    def test_includes_cbt_available(self, enriched_certificate):
        """CBT 가능 여부 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "cbt_available" in result

    def test_includes_target_job_types(self, enriched_certificate):
        """목표 직종 타입 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "target_job_types" in result
        assert isinstance(result["target_job_types"], str)

    def test_includes_target_company_types(self, enriched_certificate):
        """목표 기업 타입 필드가 포함되는지 확인."""
        result = build_user_matching_metadata(enriched_certificate)

        assert "target_company_types" in result
        assert isinstance(result["target_company_types"], str)


# ============================================================
# 기존 함수 보강 테스트 (format_certificate_text)
# ============================================================


class TestFormatCertificateTextEnhanced:
    """기존 format_certificate_text 함수의 보강된 기능 테스트."""

    def test_includes_user_matching_section(self, enriched_certificate):
        """사용자 매칭 섹션이 통합되어 있는지 확인."""
        result = format_certificate_text(enriched_certificate)

        # 새로 추가된 섹션이 있어야 함
        assert "[추천 대상]" in result

    def test_full_text_contains_all_matching_info(self, enriched_certificate):
        """전체 텍스트에 모든 매칭 정보가 포함되는지 확인."""
        result = format_certificate_text(enriched_certificate)

        # 기존 정보
        assert "정보처리기사" in result
        assert "IT/컴퓨터" in result

        # 새로 추가된 정보
        assert "비전공자" in result
        assert "직장인" in result
