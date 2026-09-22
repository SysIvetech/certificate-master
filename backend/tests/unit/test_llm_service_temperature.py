"""gpt-5-nano 모델의 temperature 파라미터 처리 테스트.

gpt-5-nano 모델은 temperature 파라미터를 지원하지 않으므로
해당 모델 사용 시 temperature 파라미터를 제외해야 합니다.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.llm.service import LLMService


class TestLLMServiceTemperature:
    """LLM 서비스의 temperature 파라미터 처리 테스트."""

    def test_should_skip_temperature_for_gpt5_nano(self):
        """gpt-5-nano 모델에서는 temperature를 건너뛰어야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        assert service.should_skip_temperature() is True

    def test_should_not_skip_temperature_for_gpt4o_mini(self):
        """gpt-5-nano 모델에서는 temperature를 사용해야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        assert service.should_skip_temperature() is False

    def test_should_not_skip_temperature_for_gpt4(self):
        """gpt-4 모델에서는 temperature를 사용해야 합니다."""
        service = LLMService()
        service.model = "gpt-4"

        assert service.should_skip_temperature() is False

    def test_build_completion_params_without_temperature(self):
        """gpt-5-nano 모델에서 completion 파라미터에 temperature가 없어야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        params = service.build_completion_params(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.4,
        )

        assert "temperature" not in params
        assert params["model"] == "gpt-5-nano"
        assert params["messages"] == [{"role": "user", "content": "test"}]

    def test_build_completion_params_with_temperature(self):
        """gpt-5-nano 모델에서 completion 파라미터에 temperature가 있어야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        params = service.build_completion_params(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.4,
        )

        assert params["temperature"] == 0.4
        assert params["model"] == "gpt-5-nano"


@pytest.mark.asyncio
class TestLLMServicePhaseIntegration:
    """LLM 서비스 Phase 메서드의 temperature 처리 통합 테스트."""

    async def test_phase1_extract_uses_build_completion_params_for_gpt5_nano(self):
        """gpt-5-nano에서 _phase1_extract가 temperature 없이 API를 호출해야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        # Mock the client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = """{
            "overview_draft": "테스트 개요",
            "difficulty": 3,
            "study_period_days": 30,
            "exam_info": {"subjects": [], "exam_type": "", "passing_criteria": ""},
            "career_info": {"use_cases": [], "related_jobs": []},
            "user_reviews": {},
            "study_guide": {},
            "official_sources": {}
        }"""

        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service._phase1_extract("테스트 자격증", "검색 결과")

        # API 호출 시 temperature가 포함되지 않았는지 확인
        call_kwargs = service.client.chat.completions.create.call_args.kwargs
        assert "temperature" not in call_kwargs

    async def test_phase1_extract_uses_temperature_for_gpt4o_mini(self):
        """gpt-5-nano에서 _phase1_extract가 temperature와 함께 API를 호출해야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        # Mock the client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = """{
            "overview_draft": "테스트 개요",
            "difficulty": 3,
            "study_period_days": 30,
            "exam_info": {"subjects": [], "exam_type": "", "passing_criteria": ""},
            "career_info": {"use_cases": [], "related_jobs": []},
            "user_reviews": {},
            "study_guide": {},
            "official_sources": {}
        }"""

        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service._phase1_extract("테스트 자격증", "검색 결과")

        # API 호출 시 temperature가 포함되었는지 확인
        call_kwargs = service.client.chat.completions.create.call_args.kwargs
        assert "temperature" in call_kwargs

    async def test_phase1_extract_logs_error_message_on_failure(self, capsys):
        """오류 발생 시 실제 오류 메시지가 로그에 출력되어야 합니다."""
        service = LLMService()
        service.model = "gpt-5-nano"

        # API 호출 시 오류 발생하도록 설정
        error_message = "Test error: Invalid request"
        service.client = MagicMock()
        service.client.chat = MagicMock()
        service.client.chat.completions = MagicMock()
        service.client.chat.completions.create = AsyncMock(
            side_effect=Exception(error_message)
        )

        with pytest.raises(Exception):
            await service._phase1_extract("테스트 자격증", "검색 결과")

        # 오류 메시지가 출력되었는지 확인
        captured = capsys.readouterr()
        assert error_message in captured.out
