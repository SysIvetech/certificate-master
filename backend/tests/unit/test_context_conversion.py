"""StructuredUserContext → RecommendationRequest 변환 테스트.

자연어 추천의 구조화된 컨텍스트를 기존 추천 요청으로 변환하는 기능을 테스트합니다.
"""


class TestContextToRequestConversion:
    """StructuredUserContext → RecommendationRequest 변환 테스트."""

    def test_conversion_function_exists(self):
        """변환 함수가 존재하는지 확인."""
        from app.schemas.recommendation import structured_to_recommendation_request

        assert callable(structured_to_recommendation_request)

    def test_goal_to_purpose_mapping(self):
        """goal → purpose 매핑 테스트."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        # 기본 컨텍스트
        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
            preferred_industries=["IT"],
        )

        request = structured_to_recommendation_request(context)

        assert request.purpose == "취업"

    def test_goal_mapping_professional_development(self):
        """'전문성 강화' → '커리어 전문성 강화' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="전문성 강화",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=180,
            difficulty_preference="중상",
            preferred_industries=["IT"],
        )

        request = structured_to_recommendation_request(context)

        assert request.purpose == "커리어 전문성 강화"

    def test_goal_mapping_personal_interest(self):
        """'개인 관심' → '개인 관심 / 교양' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="개인 관심",
            employment_status="재직 중",
            major_background="비전공자",
            weekly_study_hours=5,
            max_study_period_days=365,
            difficulty_preference="하",
            preferred_industries=[],
        )

        request = structured_to_recommendation_request(context)

        assert request.purpose == "개인 관심 / 교양"

    def test_goal_mapping_startup(self):
        """'창업' → '창업 / 실무 활용' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="창업",
            employment_status="무직",
            major_background="관련 경험 있음",
            weekly_study_hours=30,
            max_study_period_days=60,
            difficulty_preference="중",
            preferred_industries=["창업"],
        )

        request = structured_to_recommendation_request(context)

        assert request.purpose == "창업 / 실무 활용"

    def test_study_period_to_timeline_short(self):
        """30-90일 → '3개월 이하' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=20,
            max_study_period_days=60,
            difficulty_preference="중",
            preferred_industries=["IT"],
        )

        request = structured_to_recommendation_request(context)

        assert request.study_timeline == "3개월 이하"

    def test_study_period_to_timeline_medium(self):
        """91-180일 → '6개월 이하' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=15,
            max_study_period_days=150,
            difficulty_preference="중",
            preferred_industries=["IT"],
        )

        request = structured_to_recommendation_request(context)

        assert request.study_timeline == "6개월 이하"

    def test_study_period_to_timeline_long(self):
        """181-365일 → '1년 이하' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="전문성 강화",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=300,
            difficulty_preference="상",
            preferred_industries=["금융"],
        )

        request = structured_to_recommendation_request(context)

        assert request.study_timeline == "1년 이하"

    def test_study_period_to_timeline_very_long(self):
        """366일 이상 → '1년 이상' 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="전문성 강화",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=5,
            max_study_period_days=500,
            difficulty_preference="상",
            preferred_industries=["법률"],
        )

        request = structured_to_recommendation_request(context)

        assert request.study_timeline == "1년 이상"

    def test_difficulty_mapping(self):
        """difficulty_preference 매핑 테스트."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        # "하", "중하" → "쉬운 편"
        context_easy = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="하",
            preferred_industries=["IT"],
        )
        assert (
            structured_to_recommendation_request(context_easy).difficulty_preference
            == "쉬운 편"
        )

        # "중" → "중간"
        context_medium = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
            preferred_industries=["IT"],
        )
        assert (
            structured_to_recommendation_request(context_medium).difficulty_preference
            == "중간"
        )

        # "중상", "상" → "어려워도 상관없음"
        context_hard = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=20,
            max_study_period_days=180,
            difficulty_preference="상",
            preferred_industries=["IT"],
        )
        assert (
            structured_to_recommendation_request(context_hard).difficulty_preference
            == "어려워도 상관없음"
        )

    def test_preferred_industries_to_target_industries(self):
        """preferred_industries → target_industries 매핑."""
        from app.schemas.recommendation import (
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=20,
            max_study_period_days=180,
            difficulty_preference="중",
            preferred_industries=["IT", "금융", "게임"],
        )

        request = structured_to_recommendation_request(context)

        assert request.target_industries == ["IT", "금융", "게임"]

    def test_returns_valid_recommendation_request(self):
        """변환 결과가 유효한 RecommendationRequest인지 확인."""
        from app.schemas.recommendation import (
            RecommendationRequest,
            StructuredUserContext,
            structured_to_recommendation_request,
        )

        context = StructuredUserContext(
            goal="이직",
            employment_status="재직 중",
            major_background="관련 경험 있음",
            weekly_study_hours=15,
            max_study_period_days=120,
            difficulty_preference="중상",
            preferred_industries=["IT", "데이터"],
        )

        request = structured_to_recommendation_request(context)

        # RecommendationRequest 인스턴스여야 함
        assert isinstance(request, RecommendationRequest)
