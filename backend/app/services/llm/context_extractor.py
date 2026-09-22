"""Step 1: 상황 구조화 서비스.

사용자의 자연어 입력을 LLM을 통해 구조화된 JSON으로 변환합니다.
"""

import json
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.recommendation import StructuredUserContext
from app.services.study.prompts.context_extraction import (
    CONTEXT_EXTRACTION_SYSTEM_PROMPT,
    CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE,
)

# OpenAI API 타임아웃 설정 - 프록시 타임아웃(60s) 내에 완료 보장
_LLM_TIMEOUT = 20
_LLM_MAX_RETRIES = 1

logger = logging.getLogger(__name__)


class ContextExtractorService:
    """사용자 자연어 입력을 구조화된 컨텍스트로 변환하는 서비스."""

    def __init__(self, api_key: Optional[str] = None):
        """서비스를 초기화합니다.

        Args:
            api_key: OpenAI API 키. 제공되지 않으면 설정에서 로드합니다.
        """
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL_NAME

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=_LLM_TIMEOUT,
                max_retries=_LLM_MAX_RETRIES,
            )
        else:
            self.client = None

    async def extract_context(self, user_input: str) -> StructuredUserContext:
        """자연어 입력을 구조화된 사용자 컨텍스트로 변환합니다.

        Args:
            user_input: 사용자의 자연어 입력.

        Returns:
            StructuredUserContext: 구조화된 사용자 상황 정보.

        Raises:
            ValueError: API 키가 설정되지 않았거나 응답이 비어있는 경우.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        logger.info(f"[ContextExtractor] Processing user input: {user_input[:50]}...")

        response_data = await self._call_llm(user_input)

        return StructuredUserContext(**response_data)

    async def _call_llm(self, user_input: str) -> dict:
        """LLM을 호출하여 구조화된 데이터를 반환합니다.

        Args:
            user_input: 사용자의 자연어 입력.

        Returns:
            dict: LLM이 생성한 구조화된 데이터.
        """
        user_prompt = CONTEXT_EXTRACTION_USER_PROMPT_TEMPLATE.format(
            user_input=user_input
        )

        # Note: temperature 파라미터는 o1/o3 계열 모델에서 지원되지 않으므로 제거
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CONTEXT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            store=True,
            metadata={
                "service": "context_extractor",
                "method": "extract_context",
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        logger.info("[ContextExtractor] LLM response received")

        return json.loads(content)

    async def extract_context_and_query(
        self,
        user_input: str,
        selected_domains: list[str],
    ) -> tuple[StructuredUserContext, str]:
        """상황 구조화와 검색 쿼리를 동시에 생성합니다.

        기존 extract_context()와 QueryGeneratorService를 통합합니다.

        Args:
            user_input: 사용자의 자연어 입력.
            selected_domains: 사용자가 선택한 분야 목록.

        Returns:
            (StructuredUserContext, search_query) 튜플.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        logger.info(f"[ContextExtractor] Processing (unified): {user_input[:50]}...")

        from app.services.study.prompts.context_extraction import (
            UNIFIED_SYSTEM_PROMPT,
            UNIFIED_USER_PROMPT_TEMPLATE,
        )

        user_prompt = UNIFIED_USER_PROMPT_TEMPLATE.format(
            user_input=user_input,
            selected_domains=", ".join(selected_domains),
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": UNIFIED_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            store=True,
            metadata={
                "service": "context_extractor",
                "method": "extract_context_and_query",
                "domains": ", ".join(selected_domains[:3]),
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        logger.info(f"[ContextExtractor] Unified LLM raw response: {content[:200]}...")

        data = json.loads(content)

        # context 키가 없으면 최상위 레벨에서 직접 파싱 시도
        context_data = data.get("context", data)
        try:
            context = StructuredUserContext(**context_data)
        except Exception as e:
            logger.error(
                f"[ContextExtractor] Failed to parse context: {e}, data={context_data}"
            )
            # 기본값으로 폴백
            context = StructuredUserContext(
                goal=context_data.get("goal", "취업"),
                employment_status=context_data.get("employment_status", "구직 중"),
                major_background=context_data.get("major_background", "비전공자"),
                weekly_study_hours=max(
                    1, min(40, int(context_data.get("weekly_study_hours", 15)))
                ),
                max_study_period_days=max(
                    30, min(730, int(context_data.get("max_study_period_days", 180)))
                ),
                difficulty_preference=context_data.get("difficulty_preference", "중"),
                preferred_industries=context_data.get("preferred_industries", []),
            )

        search_query = data.get("search_query", user_input)

        return context, search_query


# Singleton instance
_context_extractor: Optional[ContextExtractorService] = None


def get_context_extractor() -> ContextExtractorService:
    """싱글턴 ContextExtractorService 인스턴스를 반환합니다."""
    global _context_extractor
    if _context_extractor is None:
        _context_extractor = ContextExtractorService()
    return _context_extractor
