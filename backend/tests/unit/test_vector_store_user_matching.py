"""vector_store 사용자 매칭 통합 테스트.

임베딩에 사용자 매칭 정보가 포함되는지 테스트.
"""

import pytest

from app.utils.certificate_formatter import (
    build_certificate_metadata,
    format_certificate_text,
)


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
        "career_info": {
            "industry": ["IT", "금융", "제조"],
            "use_cases": ["시스템 개발", "DB 관리"],
            "related_jobs": ["개발자", "IT 컨설턴트"],
            "job_prospects": "IT 산업 성장과 함께 수요 지속 증가",
            "average_salary": "4,500만원",
        },
        "job_market_info": {
            "job_posting_frequency": "매우 높음",
            "preferred_industries": ["IT/소프트웨어", "금융/은행"],
            "preferred_companies": ["삼성SDS", "LG CNS"],
            "requirement_type": "우대",
            "public_sector_points": "공무원 가산점 3-5%",
        },
        "cost_breakdown": {
            "exam_fee": "필기 19,400원",
            "total_estimated_cost": "30-50만원",
            "free_resources": ["큐넷 기출문제", "유튜브 강의"],
        },
        "feasibility_info": {
            "non_major_pass_rate": "40-50%",
            "self_study_possible": True,
            "minimum_study_period": 60,
            "working_adult_tips": ["출퇴근 시간 활용", "주말 집중 학습"],
        },
        "exam_schedule_detail": {
            "cbt_available": False,
            "annual_exam_count": 3,
        },
        "exam_info": {
            "exam_type": "필기+실기",
        },
    }


class TestFormatCertificateTextIntegrated:
    """format_certificate_text가 사용자 매칭 정보를 포함하는지 테스트."""

    def test_includes_user_matching_section(self, enriched_certificate):
        """사용자 매칭 섹션이 포함되는지 확인."""
        result = format_certificate_text(enriched_certificate)
        assert "[추천 대상]" in result

    def test_includes_non_major_info(self, enriched_certificate):
        """비전공자 정보가 포함되는지 확인."""
        result = format_certificate_text(enriched_certificate)
        assert "비전공자" in result

    def test_includes_working_adult_info(self, enriched_certificate):
        """직장인 정보가 포함되는지 확인."""
        result = format_certificate_text(enriched_certificate)
        assert "직장인" in result


class TestBuildCertificateMetadataIntegrated:
    """build_certificate_metadata가 사용자 매칭 메타데이터를 포함하는지 테스트."""

    def test_includes_non_major_friendly(self, enriched_certificate):
        """비전공자 친화도 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "non_major_friendly" in result
        assert isinstance(result["non_major_friendly"], bool)

    def test_includes_working_adult_friendly(self, enriched_certificate):
        """직장인 친화도 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "working_adult_friendly" in result
        assert isinstance(result["working_adult_friendly"], bool)

    def test_includes_budget_category(self, enriched_certificate):
        """예산 범주 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "budget_category" in result
        assert result["budget_category"] in ["low", "medium", "high"]

    def test_includes_weekly_hours_required(self, enriched_certificate):
        """주당 필요 학습시간 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "weekly_hours_required" in result
        assert isinstance(result["weekly_hours_required"], (int, float))

    def test_includes_target_job_types(self, enriched_certificate):
        """목표 직종 타입 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "target_job_types" in result

    def test_includes_target_company_types(self, enriched_certificate):
        """목표 기업 타입 필드가 포함되는지 확인."""
        result = build_certificate_metadata(enriched_certificate)
        assert "target_company_types" in result
