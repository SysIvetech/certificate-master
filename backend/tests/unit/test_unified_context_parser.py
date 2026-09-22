"""통합 추천용 키워드 기반 컨텍스트 파서 테스트.

TDD: LLM 호출 없이 user_input + domains에서 StructuredUserContext를 생성합니다.
"""

from app.schemas.recommendation import StructuredUserContext
from app.services.study.context_parser import build_search_query, parse_user_context


class TestParseUserContext:
    """user_input에서 StructuredUserContext를 파싱하는 테스트."""

    def test_extracts_goal_from_employment_keywords(self):
        """취업/이직 관련 키워드에서 goal을 추출."""
        ctx = parse_user_context(
            "취업 준비 중인 대학생입니다",
            domains=["IT/소프트웨어"],
        )
        assert ctx.goal == "취업"

    def test_extracts_career_change_goal(self):
        """이직 키워드."""
        ctx = parse_user_context(
            "이직을 위해 자격증을 따고 싶어요",
            domains=["금융/회계"],
        )
        assert ctx.goal == "이직"

    def test_extracts_expertise_goal(self):
        """전문성 강화 키워드."""
        ctx = parse_user_context(
            "현재 직무 전문성을 높이고 싶습니다",
            domains=["IT/소프트웨어"],
        )
        assert ctx.goal == "전문성 강화"

    def test_default_goal_when_ambiguous(self):
        """키워드가 없으면 기본값 취업."""
        ctx = parse_user_context(
            "자격증 추천해주세요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.goal == "취업"

    def test_extracts_non_major_background(self):
        """비전공자 키워드."""
        ctx = parse_user_context(
            "비전공자인데 IT 자격증 따고 싶어요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.major_background == "비전공자"

    def test_extracts_student_status(self):
        """학생 키워드."""
        ctx = parse_user_context(
            "대학생인데 졸업 전에 자격증 하나 따려고요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.employment_status == "학생"

    def test_extracts_employed_status(self):
        """재직 중 키워드."""
        ctx = parse_user_context(
            "직장 다니면서 자격증 준비하려고 합니다",
            domains=["건설/건축"],
        )
        assert ctx.employment_status == "재직 중"

    def test_extracts_study_period_months(self):
        """N개월 패턴에서 기간 추출."""
        ctx = parse_user_context(
            "3개월 안에 딸 수 있는 자격증 추천해주세요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.max_study_period_days == 90

    def test_extracts_study_period_year(self):
        """1년 패턴에서 기간 추출."""
        ctx = parse_user_context(
            "1년 정도 공부할 수 있어요",
            domains=["금융/회계"],
        )
        assert ctx.max_study_period_days == 365

    def test_extracts_easy_difficulty(self):
        """쉬운 난이도 키워드."""
        ctx = parse_user_context(
            "쉬운 자격증 추천해주세요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.difficulty_preference in ("하", "중하")

    def test_extracts_hard_difficulty(self):
        """어려운 난이도 키워드."""
        ctx = parse_user_context(
            "어렵더라도 전문적인 자격증을 원해요",
            domains=["IT/소프트웨어"],
        )
        assert ctx.difficulty_preference in ("상", "중상")

    def test_preferred_industries_from_domains(self):
        """domains에서 preferred_industries 추출."""
        ctx = parse_user_context(
            "자격증 추천해주세요",
            domains=["IT/소프트웨어", "금융/회계"],
        )
        assert (
            "IT" in ctx.preferred_industries or "소프트웨어" in ctx.preferred_industries
        )

    def test_returns_valid_structured_context(self):
        """반환값이 유효한 StructuredUserContext여야 함."""
        ctx = parse_user_context(
            "3개월 안에 딸 수 있는 쉬운 자격증이 있나요?",
            domains=["IT/소프트웨어"],
        )
        assert isinstance(ctx, StructuredUserContext)
        # 모든 필수 필드가 유효한 값
        assert ctx.goal in ["취업", "이직", "전문성 강화", "개인 관심", "창업"]
        assert ctx.employment_status in ["재직 중", "구직 중", "학생", "무직"]
        assert ctx.major_background in ["전공자", "비전공자", "관련 경험 있음"]
        assert 1 <= ctx.weekly_study_hours <= 40
        assert 30 <= ctx.max_study_period_days <= 730


class TestBuildSearchQuery:
    """domains + user_input에서 검색 쿼리를 생성하는 테스트."""

    def test_includes_domain_in_query(self):
        """도메인이 쿼리에 포함되어야 함."""
        query = build_search_query(
            "쉬운 자격증 추천",
            domains=["IT/소프트웨어"],
        )
        assert "IT" in query or "소프트웨어" in query

    def test_includes_user_input(self):
        """user_input이 쿼리에 반영되어야 함."""
        query = build_search_query(
            "3개월 안에 딸 수 있는 자격증",
            domains=["건설/건축"],
        )
        assert len(query) > 10  # 의미 있는 길이
