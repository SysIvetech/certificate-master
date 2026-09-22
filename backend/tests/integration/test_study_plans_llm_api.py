"""Integration tests for Study Plans API with LLM generation.

Tests the full flow: API → StudyPlanService → LLM → Database
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.study_plan_service import GeneratedStudyPlan, MilestoneData, TopicData


@pytest.fixture
def sample_generated_plan():
    """Sample LLM-generated study plan."""
    return GeneratedStudyPlan(
        milestones=[
            MilestoneData(
                week=1,
                title="1주차: 기초 개념 학습",
                description="소프트웨어 설계 및 데이터베이스 기초 개념을 학습합니다.",
                hours=14.0,
                completed=False,
            ),
            MilestoneData(
                week=2,
                title="2주차: 프로그래밍 언어 학습",
                description="C, Java, Python 기본 문법을 학습합니다.",
                hours=14.0,
                completed=False,
            ),
            MilestoneData(
                week=3,
                title="3주차: 기출문제 풀이",
                description="최근 3년간 기출문제를 풀이하고 오답노트를 작성합니다.",
                hours=14.0,
                completed=False,
            ),
        ],
        topics=[
            TopicData(
                name="소프트웨어 설계",
                description="소프트웨어 생명주기, UML 다이어그램 학습",
                week=1,
                hours=7.0,
                priority="high",
            ),
            TopicData(
                name="데이터베이스",
                description="SQL, 정규화, 트랜잭션 학습",
                week=1,
                hours=7.0,
                priority="high",
            ),
            TopicData(
                name="프로그래밍 언어",
                description="C, Java, Python 기본 문법",
                week=2,
                hours=14.0,
                priority="medium",
            ),
            TopicData(
                name="기출문제 1회차",
                description="2023-2025년 기출문제 풀이",
                week=3,
                hours=14.0,
                priority="high",
            ),
        ],
        total_weeks=3,
        estimated_total_hours=42.0,
    )


class TestStudyPlansLLMAPI:
    """Integration tests for Study Plans API with LLM."""

    @pytest.mark.integration
    def test_create_study_plan_with_llm_generation(
        self, authenticated_client, test_supabase_client, sample_generated_plan
    ):
        """LLM 기반 학습 계획 생성 테스트 (E2E)."""
        # Step 1: Create a test certificate
        cert_data = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "title": "정보처리기사 (LLM 테스트)",
            "raw_id": "TEST_LLM_정보처리기사",
            "overview": "소프트웨어 개발 및 데이터베이스 구축에 대한 전문 지식을 평가하는 자격증입니다.",
            "difficulty": 3,
            "study_period_days": 90,
            "exam_info": {
                "subjects": ["소프트웨어 설계", "데이터베이스", "프로그래밍 언어"],
                "exam_type": "필기+실기",
                "passing_criteria": "과목당 40점 이상, 평균 60점 이상",
                "total_fee": "40000",
            },
            "study_guide": {
                "study_methods": ["교재 중심 학습", "기출문제 위주"],
                "learning_sequence": [
                    "1단계: 기초 이론 학습 (30일)",
                    "2단계: 기출문제 풀이 (40일)",
                ],
                "time_allocation": {
                    "theory": "40%",
                    "practice": "50%",
                    "review": "10%",
                },
            },
        }

        cert_response = (
            test_supabase_client.table("certificates").insert(cert_data).execute()
        )
        certificate_id = cert_response.data[0]["id"]

        # Step 2: Mock LLM service
        with patch(
            "app.api.v1.study_plans.get_study_plan_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.generate_study_plan = AsyncMock(
                return_value=sample_generated_plan
            )
            mock_service_getter.return_value = mock_service

            # Step 3: Create study plan (milestones not provided → LLM generates)
            target_date = (date.today() + timedelta(days=90)).isoformat()
            plan_data = {
                "certificate_id": certificate_id,
                "title": "정보처리기사 학습 계획 (LLM 생성)",
                "target_date": target_date,
                "daily_study_hours": 2.0,
                # milestones 미제공 → LLM 자동 생성
            }

            response = authenticated_client.post("/api/v1/study-plans/", json=plan_data)

            # Assertions
            assert (
                response.status_code == 201
            ), f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()

            assert data["title"] == plan_data["title"]
            assert data["target_date"] == target_date
            assert data["daily_study_hours"] == 2.0
            assert data["progress_percentage"] == 0.0

            # Check LLM-generated milestones
            assert len(data["milestones"]) == 3
            milestone_1 = data["milestones"][0]
            assert milestone_1["week"] == 1
            assert "기초 개념 학습" in milestone_1["title"]
            assert milestone_1["hours"] == 14.0
            assert milestone_1["completed"] is False

            # Check LLM-generated topics
            assert len(data["topics"]) == 4
            topic_1 = data["topics"][0]
            assert topic_1["name"] == "소프트웨어 설계"
            assert topic_1["week"] == 1
            assert topic_1["priority"] == "high"

            # Verify LLM service was called
            mock_service.generate_study_plan.assert_called_once()

        # Cleanup: delete test certificate and study plan
        test_supabase_client.table("study_plans").delete().eq(
            "id", data["id"]
        ).execute()
        test_supabase_client.table("certificates").delete().eq(
            "id", certificate_id
        ).execute()

    @pytest.mark.integration
    def test_create_study_plan_manual_milestones(
        self, authenticated_client, test_supabase_client
    ):
        """수동으로 milestones 제공 시 LLM 미호출 테스트."""
        # Step 1: Create a test certificate
        cert_data = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "title": "정보처리기사 (수동 테스트)",
            "raw_id": "TEST_MANUAL_정보처리기사",
            "overview": "Test certificate for manual milestones",
            "difficulty": 3,
            "study_period_days": 90,
        }

        cert_response = (
            test_supabase_client.table("certificates").insert(cert_data).execute()
        )
        certificate_id = cert_response.data[0]["id"]

        # Step 2: Mock LLM service (should NOT be called)
        with patch(
            "app.api.v1.study_plans.get_study_plan_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.generate_study_plan = AsyncMock()
            mock_service_getter.return_value = mock_service

            # Step 3: Create study plan with manual milestones
            target_date = (date.today() + timedelta(days=90)).isoformat()
            plan_data = {
                "certificate_id": certificate_id,
                "title": "수동 학습 계획",
                "target_date": target_date,
                "daily_study_hours": 2.0,
                "milestones": [
                    {
                        "week": 1,
                        "title": "수동 마일스톤",
                        "description": "수동으로 작성한 마일스톤",
                        "hours": 10.0,
                        "completed": False,
                    }
                ],
                "topics": [
                    {
                        "name": "수동 주제",
                        "description": "수동으로 작성한 주제",
                        "week": 1,
                        "hours": 5.0,
                        "priority": "high",
                    }
                ],
            }

            response = authenticated_client.post("/api/v1/study-plans/", json=plan_data)

            # Assertions
            assert (
                response.status_code == 201
            ), f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()

            assert len(data["milestones"]) == 1
            assert data["milestones"][0]["title"] == "수동 마일스톤"

            assert len(data["topics"]) == 1
            assert data["topics"][0]["name"] == "수동 주제"

            # Verify LLM service was NOT called
            mock_service.generate_study_plan.assert_not_called()

        # Cleanup
        test_supabase_client.table("study_plans").delete().eq(
            "id", data["id"]
        ).execute()
        test_supabase_client.table("certificates").delete().eq(
            "id", certificate_id
        ).execute()

    @pytest.mark.integration
    def test_create_study_plan_llm_error_handling(
        self, authenticated_client, test_supabase_client
    ):
        """LLM 오류 발생 시 적절한 에러 응답 테스트."""
        # Step 1: Create a test certificate
        cert_data = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "title": "에러 테스트 자격증",
            "raw_id": "TEST_ERROR_자격증",
            "overview": "Test certificate for error handling",
            "difficulty": 3,
            "study_period_days": 90,
        }

        cert_response = (
            test_supabase_client.table("certificates").insert(cert_data).execute()
        )
        certificate_id = cert_response.data[0]["id"]

        # Step 2: Mock LLM service to raise error
        with patch(
            "app.api.v1.study_plans.get_study_plan_service"
        ) as mock_service_getter:
            mock_service = MagicMock()
            mock_service.generate_study_plan = AsyncMock(
                side_effect=ValueError("OPENAI_API_KEY not configured")
            )
            mock_service_getter.return_value = mock_service

            # Step 3: Create study plan (should fail)
            target_date = (date.today() + timedelta(days=90)).isoformat()
            plan_data = {
                "certificate_id": certificate_id,
                "title": "에러 테스트 학습 계획",
                "target_date": target_date,
                "daily_study_hours": 2.0,
                # milestones 미제공 → LLM 호출 → 에러 발생
            }

            response = authenticated_client.post("/api/v1/study-plans/", json=plan_data)

            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert "Failed to generate study plan" in data["detail"]

        # Cleanup
        test_supabase_client.table("certificates").delete().eq(
            "id", certificate_id
        ).execute()
