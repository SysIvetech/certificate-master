"""ContextExtractor 통합 테스트 (상황 구조화 + 쿼리 생성)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm.context_extractor import ContextExtractorService


@pytest.fixture
def mock_openai_response():
    """LLM 응답 모킹."""
    return {
        "context": {
            "goal": "취업",
            "employment_status": "학생",
            "major_background": "비전공자",
            "weekly_study_hours": 10,
            "max_study_period_days": 90,
            "difficulty_preference": "중",
            "preferred_industries": ["IT"],
        },
        "search_query": "비전공자 IT 취업 자격증 3개월 준비 가능",
    }


@pytest.mark.asyncio
async def test_extract_context_and_query(mock_openai_response):
    """상황 구조화와 검색 쿼리를 동시에 반환한다."""
    service = ContextExtractorService(api_key="test-key")

    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content=json.dumps(mock_openai_response)))
    ]

    with patch.object(
        service.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_completion,
    ):
        context, query = await service.extract_context_and_query(
            user_input="비전공자인데 3개월 안에 IT 자격증 따고 싶어요",
            selected_domains=["IT/소프트웨어"],
        )

    assert context.goal == "취업"
    assert context.major_background == "비전공자"
    assert isinstance(query, str)
    assert len(query) > 0
