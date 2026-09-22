"""ReasonGeneratorService 배치 프롬프트 및 에러 처리 테스트.

TDD: 개별 LLM 호출을 단일 배치 호출로 변경하고, 에러 처리를 검증합니다.
"""

from unittest.mock import AsyncMock

import pytest

from app.schemas.recommendation import StructuredUserContext
from app.services.study.reason_generator import ReasonGeneratorService


def make_context(**kwargs) -> StructuredUserContext:
    """테스트용 StructuredUserContext 생성."""
    defaults = {
        "goal": "취업",
        "employment_status": "구직 중",
        "major_background": "비전공자",
        "weekly_study_hours": 10,
        "max_study_period_days": 180,
        "difficulty_preference": "중",
        "preferred_industries": ["IT"],
    }
    defaults.update(kwargs)
    return StructuredUserContext(**defaults)


def make_cert_info(title: str = "테스트 자격증") -> dict:
    """테스트용 자격증 정보."""
    return {
        "title": title,
        "overview": f"{title} 개요",
        "career_info": {"related_jobs": ["테스터"]},
        "feasibility_info": {"self_study_possible": True},
    }


class TestGenerateReasonsBatchSingleCall:
    """generate_reasons_batch가 단일 LLM 호출로 모든 이유를 생성하는지 테스트."""

    @pytest.mark.asyncio
    async def test_batch_makes_single_llm_call(self):
        """N개 자격증에 대해 LLM을 1번만 호출해야 함."""
        service = ReasonGeneratorService(api_key="test-key")

        # _call_llm_batch mock: JSON 배열 반환
        certs = [make_cert_info(f"자격증{i}") for i in range(5)]
        mock_reasons = {
            f"자격증{i}": f"자격증{i}에 대한 추천 이유입니다." for i in range(5)
        }

        service._call_llm_batch = AsyncMock(return_value=mock_reasons)

        context = make_context()
        results = await service.generate_reasons_batch(context, certs)

        assert len(results) == 5
        # _call_llm_batch가 정확히 1번 호출
        service._call_llm_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_returns_reasons_in_order(self):
        """결과 순서가 입력 자격증 순서와 동일해야 함."""
        service = ReasonGeneratorService(api_key="test-key")

        certs = [make_cert_info(f"자격증{i}") for i in range(3)]
        mock_reasons = {
            "자격증0": "첫 번째 이유",
            "자격증1": "두 번째 이유",
            "자격증2": "세 번째 이유",
        }

        service._call_llm_batch = AsyncMock(return_value=mock_reasons)

        context = make_context()
        results = await service.generate_reasons_batch(context, certs)

        assert results[0] == "첫 번째 이유"
        assert results[1] == "두 번째 이유"
        assert results[2] == "세 번째 이유"

    @pytest.mark.asyncio
    async def test_batch_fallback_on_llm_failure(self):
        """LLM 호출 실패 시 기본 이유를 반환해야 함."""
        service = ReasonGeneratorService(api_key="test-key")

        service._call_llm_batch = AsyncMock(
            side_effect=ConnectionError("API 연결 실패")
        )

        context = make_context()
        certs = [make_cert_info(f"자격증{i}") for i in range(3)]

        results = await service.generate_reasons_batch(context, certs)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert f"자격증{i}" in result
            assert "적합한 자격증입니다" in result

    @pytest.mark.asyncio
    async def test_batch_fallback_on_partial_missing(self):
        """LLM 응답에서 일부 자격증이 누락된 경우 기본 이유로 대체."""
        service = ReasonGeneratorService(api_key="test-key")

        # 3개 중 1개만 응답에 포함
        mock_reasons = {
            "자격증0": "첫 번째 이유",
            # 자격증1 누락
            "자격증2": "세 번째 이유",
        }
        service._call_llm_batch = AsyncMock(return_value=mock_reasons)

        context = make_context()
        certs = [make_cert_info(f"자격증{i}") for i in range(3)]

        results = await service.generate_reasons_batch(context, certs)

        assert len(results) == 3
        assert results[0] == "첫 번째 이유"
        assert "적합한 자격증입니다" in results[1]  # 누락 → 기본 이유
        assert results[2] == "세 번째 이유"

    @pytest.mark.asyncio
    async def test_batch_fallback_on_invalid_json(self):
        """LLM이 잘못된 JSON을 반환하면 기본 이유로 대체."""
        service = ReasonGeneratorService(api_key="test-key")

        # _call_llm_batch가 ValueError(파싱 실패)를 발생
        service._call_llm_batch = AsyncMock(
            side_effect=ValueError("Invalid JSON response")
        )

        context = make_context()
        certs = [make_cert_info(f"자격증{i}") for i in range(2)]

        results = await service.generate_reasons_batch(context, certs)

        assert len(results) == 2
        for result in results:
            assert "적합한 자격증입니다" in result


class TestReasonGeneratorTimeout:
    """OpenAI 클라이언트 타임아웃 설정 테스트."""

    def test_client_has_reasonable_timeout(self):
        """AsyncOpenAI 클라이언트에 합리적인 타임아웃이 설정되어야 함.

        기본 600초(10분)는 너무 길다. 30초 이내여야 함.
        """
        service = ReasonGeneratorService(api_key="test-key")

        assert service.client is not None
        timeout = service.client.timeout
        assert timeout is not None

        # timeout이 int/float이면 직접 비교, httpx.Timeout이면 .read 사용
        if isinstance(timeout, (int, float)):
            assert timeout <= 30, f"Timeout이 너무 큼: {timeout}초"
        else:
            assert timeout.read <= 30, f"Read timeout이 너무 큼: {timeout.read}초"
