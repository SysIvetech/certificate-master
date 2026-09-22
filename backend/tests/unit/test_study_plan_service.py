"""Unit tests for StudyPlanService.

OpenAI API (GPT-4o-mini) 모델 사용.
"""

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.study_plan_service import (
    GeneratedStudyPlan,
    MilestoneData,
    StudyPlanService,
    TopicData,
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch("app.services.study_plan_service.AsyncOpenAI") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_certificate_data():
    """Sample certificate data for testing."""
    return {
        "title": "정보처리기사",
        "overview": "소프트웨어 개발 및 데이터베이스 구축에 대한 전문 지식을 평가하는 자격증입니다.",
        "difficulty": 3,
        "study_period_days": 90,
        "exam_info": {
            "subjects": [
                "소프트웨어 설계",
                "데이터베이스",
                "프로그래밍 언어",
                "정보시스템 구축관리",
            ],
            "exam_type": "필기+실기",
            "passing_criteria": "과목당 40점 이상, 평균 60점 이상",
            "total_fee": "40000",
        },
        "study_guide": {
            "study_methods": ["교재 중심 학습", "기출문제 위주"],
            "learning_sequence": [
                "1단계: 기초 이론 학습 (30일)",
                "2단계: 기출문제 풀이 (40일)",
                "3단계: 모의고사 및 최종 점검 (20일)",
            ],
            "time_allocation": {"theory": "40%", "practice": "50%", "review": "10%"},
            "recommended_books": [
                {"title": "정보처리기사 필기", "publisher": "시대에듀", "type": "필기"},
                {"title": "정보처리기사 실기", "publisher": "시대에듀", "type": "실기"},
            ],
            "success_tips": [
                "기출문제 3회 이상 반복",
                "오답노트 작성",
                "실기는 코드 암기보다 이해 중심",
            ],
        },
    }


@pytest.fixture
def sample_llm_response():
    """Sample LLM response for mocking."""
    return {
        "milestones": [
            {
                "week": 1,
                "title": "1주차: 기초 개념 학습",
                "description": "소프트웨어 설계 및 데이터베이스 기초 개념을 학습합니다.",
                "hours": 14.0,
                "completed": False,
            },
            {
                "week": 2,
                "title": "2주차: 프로그래밍 언어 학습",
                "description": "C, Java, Python 기본 문법을 학습합니다.",
                "hours": 14.0,
                "completed": False,
            },
            {
                "week": 3,
                "title": "3주차: 기출문제 풀이",
                "description": "최근 3년간 기출문제를 풀이하고 오답노트를 작성합니다.",
                "hours": 14.0,
                "completed": False,
            },
        ],
        "topics": [
            {
                "name": "소프트웨어 설계",
                "description": "소프트웨어 생명주기, UML 다이어그램 학습",
                "week": 1,
                "hours": 7.0,
                "priority": "high",
            },
            {
                "name": "데이터베이스",
                "description": "SQL, 정규화, 트랜잭션 학습",
                "week": 1,
                "hours": 7.0,
                "priority": "high",
            },
            {
                "name": "프로그래밍 언어",
                "description": "C, Java, Python 기본 문법",
                "week": 2,
                "hours": 14.0,
                "priority": "medium",
            },
            {
                "name": "기출문제 1회차",
                "description": "2023-2025년 기출문제 풀이",
                "week": 3,
                "hours": 14.0,
                "priority": "high",
            },
        ],
        "total_weeks": 3,
        "estimated_total_hours": 42.0,
    }


class TestStudyPlanService:
    """StudyPlanService unit tests."""

    def test_initialization_with_api_key(self):
        """API 키로 초기화 테스트."""
        service = StudyPlanService(api_key="test-api-key")
        assert service.api_key == "test-api-key"
        assert service.client is not None
        # OpenAI GPT 모델 사용 확인
        assert "gpt" in service.model.lower()

    def test_initialization_without_api_key(self):
        """API 키 없이 초기화 테스트 (설정에서 가져옴)."""
        # 기본 설정으로 초기화
        service = StudyPlanService()
        # OpenAI 모델 사용 확인
        assert "gpt" in service.model.lower()

    @pytest.mark.asyncio
    async def test_generate_study_plan_success(
        self, mock_openai_client, sample_certificate_data, sample_llm_response
    ):
        """학습 계획 생성 성공 테스트."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(sample_llm_response)
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        # Initialize service with mock client
        service = StudyPlanService(api_key="test-api-key")

        # Generate study plan
        target_date = date.today() + timedelta(days=90)
        result = await service.generate_study_plan(
            certificate_data=sample_certificate_data,
            target_date=target_date,
            daily_study_hours=2.0,
        )

        # Assertions
        assert isinstance(result, GeneratedStudyPlan)
        assert len(result.milestones) == 3
        assert len(result.topics) == 4
        assert result.total_weeks == 3
        assert result.estimated_total_hours == 42.0

        # Check milestone structure
        milestone = result.milestones[0]
        assert isinstance(milestone, MilestoneData)
        assert milestone.week == 1
        assert milestone.title == "1주차: 기초 개념 학습"
        assert milestone.completed is False

        # Check topic structure
        topic = result.topics[0]
        assert isinstance(topic, TopicData)
        assert topic.name == "소프트웨어 설계"
        assert topic.week == 1
        assert topic.priority == "high"

    @pytest.mark.asyncio
    async def test_generate_study_plan_no_api_key(self, sample_certificate_data):
        """API가 설정되지 않았을 때 에러 발생 테스트."""
        # 서비스 생성 후 client를 None으로 강제 설정
        service = StudyPlanService()
        service.client = None

        target_date = date.today() + timedelta(days=90)

        with pytest.raises(ValueError, match="OPENAI_API_KEY not configured"):
            await service.generate_study_plan(
                certificate_data=sample_certificate_data,
                target_date=target_date,
                daily_study_hours=2.0,
            )

    @pytest.mark.asyncio
    async def test_generate_study_plan_past_target_date(
        self, mock_openai_client, sample_certificate_data
    ):
        """과거 날짜를 목표일로 설정 시 에러 발생 테스트."""
        service = StudyPlanService(api_key="test-api-key")

        # 과거 날짜
        past_date = date.today() - timedelta(days=10)

        with pytest.raises(ValueError, match="목표일은 오늘보다 미래여야 합니다"):
            await service.generate_study_plan(
                certificate_data=sample_certificate_data,
                target_date=past_date,
                daily_study_hours=2.0,
            )

    @pytest.mark.asyncio
    async def test_generate_study_plan_empty_llm_response(
        self, mock_openai_client, sample_certificate_data
    ):
        """LLM 응답이 비어있을 때 에러 발생 테스트."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = None
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = StudyPlanService(api_key="test-api-key")
        target_date = date.today() + timedelta(days=90)

        with pytest.raises(ValueError, match="Empty response from LLM"):
            await service.generate_study_plan(
                certificate_data=sample_certificate_data,
                target_date=target_date,
                daily_study_hours=2.0,
            )

    @pytest.mark.asyncio
    async def test_generate_study_plan_llm_call_parameters(
        self, mock_openai_client, sample_certificate_data, sample_llm_response
    ):
        """LLM 호출 시 올바른 파라미터 전달 확인."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = json.dumps(sample_llm_response)
        mock_openai_client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        service = StudyPlanService(api_key="test-api-key")
        target_date = date.today() + timedelta(days=90)

        await service.generate_study_plan(
            certificate_data=sample_certificate_data,
            target_date=target_date,
            daily_study_hours=2.0,
        )

        # LLM 호출 확인
        mock_openai_client.chat.completions.create.assert_called_once()
        call_args = mock_openai_client.chat.completions.create.call_args

        # Check model (OpenAI GPT 사용)
        assert "gpt" in call_args.kwargs["model"].lower()

        # Check messages structure
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Check system prompt contains certificate info
        system_content = messages[0]["content"]
        assert "정보처리기사" in system_content
        assert "난이도: 3/5" in system_content
        assert "90일" in system_content

        # Check temperature
        assert call_args.kwargs["temperature"] == 0.3

        # Check response format
        assert call_args.kwargs["response_format"] == {"type": "json_object"}
