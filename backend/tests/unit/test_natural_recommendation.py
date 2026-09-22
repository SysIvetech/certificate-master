"""자연어 기반 자격증 추천 시스템 테스트.

TDD 방식으로 구현된 테스트 모듈입니다.
"""

import pytest
from pydantic import ValidationError


# Step 1: 스키마 테스트
class TestStructuredUserContextSchema:
    """StructuredUserContext 스키마 테스트."""

    def test_valid_context_creation(self):
        """유효한 사용자 컨텍스트 생성 테스트."""
        from app.schemas.recommendation import StructuredUserContext

        context = StructuredUserContext(
            goal="취업",
            employment_status="구직 중",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
            preferred_industries=["IT", "금융"],
        )

        assert context.goal == "취업"
        assert context.employment_status == "구직 중"
        assert context.major_background == "비전공자"
        assert context.weekly_study_hours == 10
        assert context.max_study_period_days == 90
        assert context.difficulty_preference == "중"
        assert context.preferred_industries == ["IT", "금융"]

    def test_goal_validation(self):
        """goal 필드 유효성 검증 테스트."""
        from app.schemas.recommendation import StructuredUserContext

        # 유효한 goal 값들
        valid_goals = ["취업", "이직", "전문성 강화", "개인 관심", "창업"]
        for goal in valid_goals:
            context = StructuredUserContext(
                goal=goal,
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=10,
                max_study_period_days=90,
                difficulty_preference="중",
            )
            assert context.goal == goal

    def test_invalid_goal_raises_error(self):
        """잘못된 goal 값은 ValidationError를 발생시켜야 함."""
        from app.schemas.recommendation import StructuredUserContext

        with pytest.raises(ValidationError):
            StructuredUserContext(
                goal="잘못된 목표",  # 유효하지 않은 값
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=10,
                max_study_period_days=90,
                difficulty_preference="중",
            )

    def test_weekly_study_hours_range(self):
        """weekly_study_hours 범위 검증 (1-40)."""
        from app.schemas.recommendation import StructuredUserContext

        # 최소값
        context_min = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=1,
            max_study_period_days=90,
            difficulty_preference="중",
        )
        assert context_min.weekly_study_hours == 1

        # 최대값
        context_max = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=40,
            max_study_period_days=90,
            difficulty_preference="중",
        )
        assert context_max.weekly_study_hours == 40

        # 범위 초과
        with pytest.raises(ValidationError):
            StructuredUserContext(
                goal="취업",
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=0,  # 1 미만
                max_study_period_days=90,
                difficulty_preference="중",
            )

        with pytest.raises(ValidationError):
            StructuredUserContext(
                goal="취업",
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=41,  # 40 초과
                max_study_period_days=90,
                difficulty_preference="중",
            )

    def test_max_study_period_days_range(self):
        """max_study_period_days 범위 검증 (30-730)."""
        from app.schemas.recommendation import StructuredUserContext

        # 최소값
        context_min = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=30,
            difficulty_preference="중",
        )
        assert context_min.max_study_period_days == 30

        # 최대값
        context_max = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=730,
            difficulty_preference="중",
        )
        assert context_max.max_study_period_days == 730

        # 범위 초과
        with pytest.raises(ValidationError):
            StructuredUserContext(
                goal="취업",
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=10,
                max_study_period_days=29,  # 30 미만
                difficulty_preference="중",
            )

    def test_preferred_industries_max_items(self):
        """preferred_industries 최대 5개 제한 검증."""
        from app.schemas.recommendation import StructuredUserContext

        # 5개는 OK
        context = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
            preferred_industries=["IT", "금융", "건설", "의료", "교육"],
        )
        assert len(context.preferred_industries) == 5

        # 6개는 에러
        with pytest.raises(ValidationError):
            StructuredUserContext(
                goal="취업",
                employment_status="재직 중",
                major_background="전공자",
                weekly_study_hours=10,
                max_study_period_days=90,
                difficulty_preference="중",
                preferred_industries=["IT", "금융", "건설", "의료", "교육", "물류"],
            )

    def test_default_preferred_industries(self):
        """preferred_industries 기본값은 빈 리스트."""
        from app.schemas.recommendation import StructuredUserContext

        context = StructuredUserContext(
            goal="취업",
            employment_status="재직 중",
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
        )
        assert context.preferred_industries == []


class TestNaturalLanguageRequestSchema:
    """NaturalLanguageRequest 스키마 테스트."""

    def test_valid_request(self):
        """유효한 자연어 요청 생성 테스트."""
        from app.schemas.recommendation import NaturalLanguageRequest

        request = NaturalLanguageRequest(
            user_input="비전공자인데 IT 분야 취업을 위해 자격증 준비하고 싶어요"
        )
        assert "비전공자" in request.user_input

    def test_min_length_validation(self):
        """user_input 최소 길이 검증 (10자)."""
        from app.schemas.recommendation import NaturalLanguageRequest

        # 10자 OK
        request = NaturalLanguageRequest(user_input="자격증 추천해주세요")
        assert len(request.user_input) >= 10

        # 10자 미만은 에러
        with pytest.raises(ValidationError):
            NaturalLanguageRequest(user_input="짧은 요청")

    def test_max_length_validation(self):
        """user_input 최대 길이 검증 (1000자)."""
        from app.schemas.recommendation import NaturalLanguageRequest

        # 1000자 OK
        long_text = "자" * 1000
        request = NaturalLanguageRequest(user_input=long_text)
        assert len(request.user_input) == 1000

        # 1001자 이상은 에러
        with pytest.raises(ValidationError):
            NaturalLanguageRequest(user_input="자" * 1001)


class TestNaturalLanguageResponseSchema:
    """NaturalLanguageResponse 스키마 테스트."""

    def test_valid_response(self):
        """유효한 자연어 응답 생성 테스트."""
        from app.schemas.recommendation import (
            NaturalLanguageResponse,
            StructuredUserContext,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="구직 중",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        response = NaturalLanguageResponse(
            structured_context=context,
            recommendations=[],
            query_used="비전공자 IT 취업 자격증",
            follow_up_question="어떤 IT 분야에 관심이 있으신가요?",
            total_matched=0,
        )

        assert response.structured_context == context
        assert response.recommendations == []
        assert response.query_used == "비전공자 IT 취업 자격증"
        assert response.follow_up_question is not None
        assert response.total_matched == 0

    def test_optional_follow_up_question(self):
        """follow_up_question은 선택적 필드."""
        from app.schemas.recommendation import (
            NaturalLanguageResponse,
            StructuredUserContext,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="구직 중",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        response = NaturalLanguageResponse(
            structured_context=context,
            recommendations=[],
            query_used="비전공자 IT 취업 자격증",
            total_matched=0,
        )

        assert response.follow_up_question is None


# Step 2: 프롬프트 모듈 테스트
class TestContextExtractionPrompt:
    """상황 구조화 프롬프트 테스트."""

    def test_prompt_exists(self):
        """프롬프트가 존재하고 문자열인지 확인."""
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
            CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE,
        )

        assert isinstance(CONTEXT_EXTRACTION_SYSTEM_PROMPT, str)
        assert isinstance(CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE, str)

    def test_system_prompt_contains_required_fields(self):
        """시스템 프롬프트에 필수 필드가 포함되어 있는지 확인."""
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
        )

        required_fields = [
            "goal",
            "employment_status",
            "major_background",
            "weekly_study_hours",
            "max_study_period_days",
            "difficulty_preference",
            "preferred_industries",
        ]

        for field in required_fields:
            assert field in CONTEXT_EXTRACTION_SYSTEM_PROMPT, f"Missing field: {field}"

    def test_user_prompt_template_has_placeholder(self):
        """사용자 프롬프트 템플릿에 {user_input} 플레이스홀더가 있는지 확인."""
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE,
        )

        assert "{user_input}" in CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE

    def test_user_prompt_formatting(self):
        """사용자 프롬프트 포맷팅이 정상 동작하는지 확인."""
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE,
        )

        user_input = "비전공자인데 IT 취업 준비 중입니다"
        formatted = CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            user_input=user_input
        )

        assert user_input in formatted


class TestQueryGenerationPrompt:
    """검색 쿼리 생성 프롬프트 테스트."""

    def test_prompt_exists(self):
        """프롬프트가 존재하고 문자열인지 확인."""
        from app.services.study.prompts.query_generation import (
            QUERY_GENERATION_SYSTEM_PROMPT,
            QUERY_GENERATION_USER_PROMPT_TEMPLATE,
        )

        assert isinstance(QUERY_GENERATION_SYSTEM_PROMPT, str)
        assert isinstance(QUERY_GENERATION_USER_PROMPT_TEMPLATE, str)

    def test_user_prompt_template_has_placeholder(self):
        """사용자 프롬프트 템플릿에 {structured_context} 플레이스홀더가 있는지 확인."""
        from app.services.study.prompts.query_generation import (
            QUERY_GENERATION_USER_PROMPT_TEMPLATE,
        )

        assert "{structured_context}" in QUERY_GENERATION_USER_PROMPT_TEMPLATE


class TestRecommendationReasonPrompt:
    """추천 이유 생성 프롬프트 테스트."""

    def test_prompt_exists(self):
        """프롬프트가 존재하고 문자열인지 확인."""
        from app.services.study.prompts.recommendation_reason import (
            RECOMMENDATION_REASON_SYSTEM_PROMPT,
            RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE,
        )

        assert isinstance(RECOMMENDATION_REASON_SYSTEM_PROMPT, str)
        assert isinstance(RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE, str)

    def test_user_prompt_template_has_placeholders(self):
        """사용자 프롬프트 템플릿에 필요한 플레이스홀더가 있는지 확인."""
        from app.services.study.prompts.recommendation_reason import (
            RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE,
        )

        assert "{user_context}" in RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE
        assert "{certificate_info}" in RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE


# Step 3: 서비스 클래스 테스트
class TestContextExtractorService:
    """ContextExtractorService 테스트."""

    def test_service_exists(self):
        """서비스 클래스가 존재하는지 확인."""
        from app.services.llm.context_extractor import ContextExtractorService

        assert ContextExtractorService is not None

    def test_service_has_extract_method(self):
        """extract_context 메서드가 존재하는지 확인."""
        from app.services.llm.context_extractor import ContextExtractorService

        service = ContextExtractorService()
        assert hasattr(service, "extract_context")
        assert callable(service.extract_context)

    @pytest.mark.asyncio
    async def test_extract_context_returns_structured_context(self):
        """extract_context가 StructuredUserContext를 반환하는지 확인 (Mock)."""
        from unittest.mock import AsyncMock, patch

        from app.schemas.recommendation import StructuredUserContext
        from app.services.llm.context_extractor import ContextExtractorService

        # LLM 호출을 Mock 처리
        mock_response = {
            "goal": "취업",
            "employment_status": "학생",
            "major_background": "비전공자",
            "weekly_study_hours": 15,
            "max_study_period_days": 90,
            "difficulty_preference": "중",
            "preferred_industries": ["IT", "데이터"],
        }

        service = ContextExtractorService()

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await service.extract_context(
                "비전공자인데 IT 분야 취업 준비 중입니다"
            )

            assert isinstance(result, StructuredUserContext)
            assert result.goal == "취업"
            assert result.major_background == "비전공자"


class TestReasonGeneratorService:
    """ReasonGeneratorService 테스트."""

    def test_service_exists(self):
        """서비스 클래스가 존재하는지 확인."""
        from app.services.study.reason_generator import ReasonGeneratorService

        assert ReasonGeneratorService is not None

    def test_service_has_generate_method(self):
        """generate_reason 메서드가 존재하는지 확인."""
        from app.services.study.reason_generator import ReasonGeneratorService

        service = ReasonGeneratorService()
        assert hasattr(service, "generate_reason")
        assert callable(service.generate_reason)

    @pytest.mark.asyncio
    async def test_generate_reason_returns_string(self):
        """generate_reason이 문자열을 반환하는지 확인 (Mock)."""
        from unittest.mock import AsyncMock, patch

        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.reason_generator import ReasonGeneratorService

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=15,
            max_study_period_days=90,
            difficulty_preference="중",
            preferred_industries=["IT"],
        )

        cert_info = {
            "title": "정보처리기사",
            "overview": "IT 분야 국가기술자격증",
        }

        service = ReasonGeneratorService()

        with patch.object(service, "_call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "IT 취업에 유리한 자격증입니다."

            result = await service.generate_reason(context, cert_info)

            assert isinstance(result, str)
            assert len(result) > 0


# Step 3 (계속): NaturalRecommendationService 통합 테스트
class TestNaturalRecommendationService:
    """NaturalRecommendationService 통합 테스트."""

    def test_service_exists(self):
        """서비스 클래스가 존재하는지 확인."""
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        assert NaturalRecommendationService is not None

    def test_service_has_get_recommendations_method(self):
        """get_recommendations 메서드가 존재하는지 확인."""
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        # db 파라미터는 None으로 Mock
        service = NaturalRecommendationService(db=None)
        assert hasattr(service, "get_recommendations")
        assert callable(service.get_recommendations)

    def test_service_has_apply_hard_filters_method(self):
        """_apply_hard_filters 메서드가 존재하는지 확인."""
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        service = NaturalRecommendationService(db=None)
        assert hasattr(service, "_apply_hard_filters")
        assert callable(service._apply_hard_filters)

    def test_service_has_calculate_final_score_method(self):
        """_calculate_final_score 메서드가 존재하는지 확인."""
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        service = NaturalRecommendationService(db=None)
        assert hasattr(service, "_calculate_final_score")
        assert callable(service._calculate_final_score)


# Step 3 (계속): 하드 필터링 로직 테스트
class TestHardFiltering:
    """하드 필터링 로직 테스트."""

    def test_non_major_filter(self):
        """비전공자 필터 테스트: self_study_possible이 True인 자격증만 통과."""
        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",  # 비전공자
            weekly_study_hours=15,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        service = NaturalRecommendationService(db=None)

        # self_study_possible=True인 자격증
        cert_ok = {
            "id": "1",
            "title": "정보처리기사",
            "feasibility_info": {"self_study_possible": True},
            "study_period_days": 60,
        }

        # self_study_possible=False인 자격증
        cert_fail = {
            "id": "2",
            "title": "변호사",
            "feasibility_info": {"self_study_possible": False},
            "study_period_days": 60,
        }

        filtered = service._apply_hard_filters([cert_ok, cert_fail], context)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_working_adult_filter(self):
        """재직자 필터 테스트: max_study_period_days 이내 자격증만 통과."""
        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        context = StructuredUserContext(
            goal="이직",
            employment_status="재직 중",  # 재직자
            major_background="전공자",
            weekly_study_hours=10,
            max_study_period_days=90,  # 최대 90일
            difficulty_preference="중",
        )

        service = NaturalRecommendationService(db=None)

        # 60일 소요 자격증 (통과)
        cert_ok = {
            "id": "1",
            "title": "정보처리기사",
            "study_period_days": 60,
        }

        # 180일 소요 자격증 (실패)
        cert_fail = {
            "id": "2",
            "title": "기술사",
            "study_period_days": 180,
        }

        filtered = service._apply_hard_filters([cert_ok, cert_fail], context)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_weekly_hours_filter(self):
        """주당 학습시간 필터 테스트: weekly_hours_required <= weekly_study_hours * 1.5."""
        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=10,  # 주 10시간 → 최대 15시간까지 허용
            max_study_period_days=180,
            difficulty_preference="중",
        )

        service = NaturalRecommendationService(db=None)

        # weekly_hours_required=12 (통과: 12 <= 15)
        cert_ok = {
            "id": "1",
            "title": "정보처리기사",
            "study_period_days": 90,
            "feasibility_info": {"weekly_hours_required": 12},
        }

        # weekly_hours_required=20 (실패: 20 > 15)
        cert_fail = {
            "id": "2",
            "title": "기술사",
            "study_period_days": 90,
            "feasibility_info": {"weekly_hours_required": 20},
        }

        filtered = service._apply_hard_filters([cert_ok, cert_fail], context)

        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"


# Step 3 (계속): 점수 계산 로직 테스트
class TestScoreCalculation:
    """점수 계산 로직 테스트."""

    def test_calculate_final_score_with_similarity(self):
        """유사도 기반 점수 계산 테스트."""
        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=15,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        service = NaturalRecommendationService(db=None)

        cert = {
            "id": "1",
            "title": "정보처리기사",
            "job_market_info": {"job_posting_frequency": "많음"},
            "feasibility_info": {"self_study_possible": True},
        }

        # 유사도 0.8 → 50% 반영 → 40점 기본
        score = service._calculate_final_score(cert, 0.8, context)

        # 점수가 0-100 범위인지 확인
        assert 0 <= score <= 100

    def test_calculate_final_score_with_job_market_bonus(self):
        """채용 시장 보너스 점수 테스트."""
        from app.schemas.recommendation import StructuredUserContext
        from app.services.study.natural_recommendation_service import (
            NaturalRecommendationService,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=15,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        service = NaturalRecommendationService(db=None)

        # 채용 공고 빈도 "매우 많음" → +20점
        cert_high = {
            "id": "1",
            "title": "정보처리기사",
            "job_market_info": {"job_posting_frequency": "매우 많음"},
        }

        # 채용 공고 빈도 "적음" → +0점
        cert_low = {
            "id": "2",
            "title": "기타 자격증",
            "job_market_info": {"job_posting_frequency": "적음"},
        }

        score_high = service._calculate_final_score(cert_high, 0.5, context)
        score_low = service._calculate_final_score(cert_low, 0.5, context)

        # 채용 빈도 높은 자격증이 더 높은 점수
        assert score_high > score_low


# Step 4: API 엔드포인트 테스트
class TestNaturalRecommendationAPI:
    """자연어 추천 API 엔드포인트 테스트."""

    def test_active_endpoints_exist(self):
        """활성 엔드포인트가 라우터에 등록되어 있는지 확인."""
        from app.api.v1.recommendations import router

        routes = [route.path for route in router.routes]
        # /natural은 제거됨, /unified와 /structured가 활성
        assert "/unified" in routes
        assert "/structured" in routes
        assert "/natural" not in routes

    def test_request_validation(self):
        """요청 스키마 검증 테스트."""
        from app.schemas.recommendation import NaturalLanguageRequest

        # 유효한 요청
        valid_request = NaturalLanguageRequest(
            user_input="비전공자인데 IT 분야 취업을 위해 자격증 준비하고 싶어요"
        )
        assert valid_request.user_input is not None

    def test_response_schema(self):
        """응답 스키마 테스트."""
        from app.schemas.recommendation import (
            NaturalLanguageResponse,
            StructuredUserContext,
        )

        context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="비전공자",
            weekly_study_hours=10,
            max_study_period_days=90,
            difficulty_preference="중",
        )

        response = NaturalLanguageResponse(
            structured_context=context,
            recommendations=[],
            query_used="test query",
            total_matched=0,
        )

        assert response.structured_context is not None
        assert response.recommendations == []
        assert response.query_used == "test query"
