"""개선된 4단계 규칙 기반 컨텍스트 파서 테스트."""

import pytest

from app.schemas.recommendation import StructuredUserContext
from app.services.search.context_parser import EnhancedContextParser


@pytest.fixture
def parser():
    return EnhancedContextParser()


class TestGoalExtraction:
    def test_employment_keyword(self, parser):
        ctx = parser.parse("취업 준비 중인 대학생입니다")
        assert ctx.goal == "취업"

    def test_employment_from_graduation(self, parser):
        ctx = parser.parse("졸업 후 취업에 유리한 자격증")
        assert ctx.goal == "취업"

    def test_career_change(self, parser):
        ctx = parser.parse("이직을 위해 자격증을 따고 싶어요")
        assert ctx.goal == "이직"

    def test_career_strength(self, parser):
        ctx = parser.parse("승진에 도움되는 자격증 추천해주세요")
        assert ctx.goal == "전문성 강화"

    def test_self_development(self, parser):
        ctx = parser.parse("취미로 관심 있는 자격증을 알아보고 있어요")
        assert ctx.goal == "개인 관심"

    def test_business(self, parser):
        ctx = parser.parse("창업을 위해 필요한 자격증이 뭔가요")
        assert ctx.goal == "창업"

    def test_default_goal(self, parser):
        ctx = parser.parse("자격증 추천해주세요")
        assert ctx.goal == "취업"


class TestEmploymentExtraction:
    def test_student(self, parser):
        ctx = parser.parse("대학생인데 자격증 따고 싶어요")
        assert ctx.employment_status == "학생"

    def test_employed(self, parser):
        ctx = parser.parse("직장 다니면서 자격증 준비하려고 합니다")
        assert ctx.employment_status == "재직 중"

    def test_job_seeking(self, parser):
        ctx = parser.parse("구직 중인데 도움될 자격증 추천해주세요")
        assert ctx.employment_status == "구직 중"


class TestMajorExtraction:
    def test_non_major(self, parser):
        ctx = parser.parse("비전공자인데 IT 자격증 따고 싶어요")
        assert ctx.major_background == "비전공자"

    def test_major(self, parser):
        ctx = parser.parse("전공이 컴퓨터공학이에요")
        assert ctx.major_background == "전공자"


class TestNumericExtraction:
    def test_daily_hours(self, parser):
        ctx = parser.parse("하루 3시간 공부 가능합니다")
        assert ctx.weekly_study_hours == 21

    def test_weekly_hours(self, parser):
        ctx = parser.parse("주 15시간 정도 투자할 수 있어요")
        assert ctx.weekly_study_hours == 15

    def test_study_period_months(self, parser):
        ctx = parser.parse("3개월 안에 딸 수 있는 자격증")
        assert ctx.max_study_period_days == 90

    def test_study_period_year(self, parser):
        ctx = parser.parse("1년 정도 준비할 수 있습니다")
        assert ctx.max_study_period_days == 365


class TestDifficultyExtraction:
    def test_easy(self, parser):
        ctx = parser.parse("쉬운 자격증 추천해주세요")
        assert ctx.difficulty_preference in ("하", "중하")

    def test_hard(self, parser):
        ctx = parser.parse("어렵더라도 전문적인 자격증")
        assert ctx.difficulty_preference in ("상", "중상")


class TestDomainInference:
    def test_it_domain_from_text(self, parser):
        ctx = parser.parse("정보처리기사 따고 싶어요")
        assert "IT" in str(ctx.preferred_industries)

    def test_construction_domain_from_text(self, parser):
        ctx = parser.parse("건축기사 자격증 추천해주세요")
        assert any("건설" in ind or "건축" in ind for ind in ctx.preferred_industries)

    def test_explicit_domains_used(self, parser):
        ctx = parser.parse(
            "자격증 추천해주세요", domains=["IT/소프트웨어", "금융/회계"]
        )
        assert len(ctx.preferred_industries) > 0


class TestCooccurrence:
    def test_non_major_employment_combination(self, parser):
        ctx = parser.parse("비전공자인데 취업 준비하고 있어요")
        assert ctx.major_background == "비전공자"
        assert ctx.goal == "취업"

    def test_worker_weekend_combination(self, parser):
        ctx = parser.parse("직장인이라 주말에만 공부 가능해요")
        assert ctx.employment_status == "재직 중"
        assert ctx.weekly_study_hours <= 15


class TestOutputValidity:
    def test_returns_structured_context(self, parser):
        ctx = parser.parse("3개월 안에 쉬운 자격증 추천")
        assert isinstance(ctx, StructuredUserContext)
        assert ctx.goal in ["취업", "이직", "전문성 강화", "개인 관심", "창업"]
        assert ctx.employment_status in ["재직 중", "구직 중", "학생", "무직"]
        assert ctx.major_background in ["전공자", "비전공자", "관련 경험 있음"]
        assert 1 <= ctx.weekly_study_hours <= 40
        assert 30 <= ctx.max_study_period_days <= 730
