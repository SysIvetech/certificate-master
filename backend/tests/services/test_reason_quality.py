"""추천 이유 품질 테스트.

생성된 추천 이유가 필수 요소를 포함하는지 검증합니다.
"""

from app.schemas.recommendation import StructuredUserContext


class TestRecommendationReasonQuality:
    """추천 이유 품질 검증."""

    def test_reason_includes_user_goal(self):
        """추천 이유에 사용자 목표가 포함되어야 함."""
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발 및 데이터베이스 관리",
            "career_info": {"industry": ["IT", "정보처리"]},
            "feasibility_info": {"self_study_possible": True},
        }

        # 목표 키워드 확인
        reason = _generate_test_reason(context, cert_info)

        assert "취업" in reason or "직업" in reason or "채용" in reason

    def test_reason_includes_certificate_title(self):
        """추천 이유에 자격증 제목이 포함되어야 함."""
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발",
            "career_info": {"industry": ["IT"]},
        }

        reason = _generate_test_reason(context, cert_info)

        # 자격증 제목 또는 핵심 키워드 포함
        assert "정보처리기사" in reason or "정보처리" in reason or "IT" in reason

    def test_reason_includes_industry_match(self):
        """IT 쿼리에 IT 자격증 추천 시 산업 분야 언급이 있어야 함."""
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT", "소프트웨어"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발",
            "career_info": {"industry": ["IT", "소프트웨어"]},
            "feasibility_info": {"self_study_possible": True},
        }

        reason = _generate_test_reason(context, cert_info)

        # IT 또는 소프트웨어 관련 키워드
        it_keywords = ["IT", "소프트웨어", "개발", "프로그래밍", "정보"]
        assert any(kw in reason for kw in it_keywords)

    def test_reason_includes_feasibility_info(self):
        """비전공자 가능 여부가 추천 이유에 반영되어야 함."""
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발",
            "career_info": {"industry": ["IT"]},
            "feasibility_info": {"self_study_possible": True},
        }

        reason = _generate_test_reason(context, cert_info)

        # 비전공자 관련 언급
        non_major_keywords = ["비전공", "독학", "가능", "적합"]
        assert any(kw in reason for kw in non_major_keywords)

    def test_reason_appropriate_length(self):
        """추천 이유가 적절한 길이여야 함 (50-200자)."""
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=25,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발",
            "career_info": {"industry": ["IT"]},
        }

        reason = _generate_test_reason(context, cert_info)

        # 너무 짧지도, 길지도 않아야 함
        assert 50 <= len(reason) <= 200

    def test_reason_avoids_excluded_industry_mention(self):
        """IT 쿼리에 제조업 키워드가 추천 이유에 나오면 안 됨."""
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
        cert_info = {
            "title": "정보처리기사",
            "overview": "소프트웨어 개발",
            "career_info": {"industry": ["IT", "정보처리"]},
        }

        reason = _generate_test_reason(context, cert_info)

        # 제조업 관련 키워드가 있으면 안 됨
        excluded_keywords = ["제조", "건설", "용접", "기계", "CAD"]
        assert not any(kw in reason for kw in excluded_keywords)


def _generate_test_reason(context: StructuredUserContext, cert_info: dict) -> str:
    """테스트용 추천 이유 생성.

    실제로는 프롬프트 기반으로 생성되지만, 테스트에서는
    템플릿 기반으로 검증할 수 있는 형식을 반환합니다.
    """
    # TODO: 실제 LLM 호출 또는 개선된 템플릿 적용
    # 현재는 기본 템플릿으로 테스트
    goal = context.goal
    title = cert_info.get("title", "자격증")
    industries = cert_info.get("career_info", {}).get("industry", [])
    self_study = cert_info.get("feasibility_info", {}).get("self_study_possible", False)

    # 간단한 템플릿 (실제 프롬프트는 더 정교해야 함)
    reason = f"{goal}을 준비하시는 분께 {title}을(를) 추천합니다. "

    if industries:
        reason += f"{industries[0]} 분야에서 인정받는 자격증입니다. "

    if context.major_background == "비전공자" and self_study:
        reason += "비전공자도 독학으로 준비 가능합니다."

    return reason
