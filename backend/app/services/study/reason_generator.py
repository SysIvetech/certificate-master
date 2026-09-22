"""Step 5: 추천 이유 생성 서비스.

사용자 상황과 자격증 정보를 바탕으로 개인화된 추천 이유를 생성합니다.
배치 프롬프트 방식으로 N개 자격증을 1회 LLM 호출로 처리합니다.
"""

import json
import logging
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.recommendation import StructuredUserContext
from app.services.study.prompts.recommendation_reason import (
    RECOMMENDATION_REASON_BATCH_USER_PROMPT_TEMPLATE,
    RECOMMENDATION_REASON_SYSTEM_PROMPT,
    RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE,
)

logger = logging.getLogger(__name__)

# OpenAI API 타임아웃 (초) - 프록시 타임아웃(60s) 내에 fallback 실행 보장
_LLM_TIMEOUT = 20
_LLM_MAX_RETRIES = 1  # 총 2회 시도 (initial + 1 retry), 최대 ~41초


class ReasonGeneratorService:
    """개인화된 추천 이유를 생성하는 서비스."""

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

    async def generate_reason(
        self,
        context: StructuredUserContext,
        certificate_info: dict[str, Any],
    ) -> str:
        """사용자 상황과 자격증 정보를 바탕으로 추천 이유를 생성합니다.

        단일 자격증용. 배치 처리에는 generate_reasons_batch()를 사용하세요.

        Args:
            context: 구조화된 사용자 상황 정보.
            certificate_info: 자격증 정보 딕셔너리.

        Returns:
            str: 개인화된 추천 이유 (2-3문장).

        Raises:
            ValueError: API 키가 설정되지 않았거나 응답이 비어있는 경우.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        cert_title = certificate_info.get("title", "자격증")
        logger.info(f"[ReasonGenerator] Generating reason for: {cert_title}")

        reason = await self._call_llm(context, certificate_info)

        return reason.strip()

    async def _call_llm(
        self,
        context: StructuredUserContext,
        certificate_info: dict[str, Any],
    ) -> str:
        """LLM을 호출하여 단일 추천 이유를 생성합니다.

        Args:
            context: 구조화된 사용자 상황 정보.
            certificate_info: 자격증 정보 딕셔너리.

        Returns:
            str: 생성된 추천 이유.
        """
        context_json = context.model_dump_json(indent=2)
        cert_json = json.dumps(certificate_info, ensure_ascii=False, indent=2)

        user_prompt = RECOMMENDATION_REASON_USER_PROMPT_TEMPLATE.format(
            user_context=context_json,
            certificate_info=cert_json,
        )

        # Note: temperature 파라미터는 o1/o3 계열 모델에서 지원되지 않으므로 제거
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RECOMMENDATION_REASON_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            store=True,
            metadata={
                "service": "reason_generator",
                "method": "single",
                "cert_title": cert_json[:100],
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        logger.info(
            f"[ReasonGenerator] Generated reason for {certificate_info.get('title', 'cert')}"
        )

        return content

    async def _call_llm_batch(
        self,
        context: StructuredUserContext,
        certificates: list[dict[str, Any]],
    ) -> dict[str, str]:
        """1회 LLM 호출로 여러 자격증의 추천 이유를 생성합니다.

        Args:
            context: 구조화된 사용자 상황 정보.
            certificates: 자격증 정보 리스트.

        Returns:
            dict[str, str]: {자격증_title: 추천_이유} 매핑.

        Raises:
            ValueError: API 키 미설정, 응답 비어있음, JSON 파싱 실패.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        context_json = context.model_dump_json(indent=2)
        certs_json = json.dumps(
            [
                {
                    "title": cert.get("title", "자격증"),
                    "overview": cert.get("overview", ""),
                    "career_info": cert.get("career_info", {}),
                    "feasibility_info": cert.get("feasibility_info", {}),
                }
                for cert in certificates
            ],
            ensure_ascii=False,
            indent=2,
        )

        titles = [cert.get("title", "자격증") for cert in certificates]
        logger.info(
            f"[ReasonGenerator] Batch generating reasons for {len(certificates)} certs: "
            f"{', '.join(titles[:3])}{'...' if len(titles) > 3 else ''}"
        )

        user_prompt = RECOMMENDATION_REASON_BATCH_USER_PROMPT_TEMPLATE.format(
            user_context=context_json,
            certificates_list=certs_json,
            certificate_count=len(certificates),
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": RECOMMENDATION_REASON_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            store=True,
            metadata={
                "service": "reason_generator",
                "method": "batch",
                "cert_count": str(len(certificates)),
            },
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from LLM")

        # JSON 파싱
        parsed = json.loads(content)

        # 응답이 {"reasons": {...}} 형태일 수 있음
        if "reasons" in parsed and isinstance(parsed["reasons"], dict):
            result = parsed["reasons"]
        elif isinstance(parsed, dict):
            result = parsed
        else:
            raise ValueError(f"Unexpected response format: {type(parsed)}")

        logger.info(f"[ReasonGenerator] Batch generated {len(result)} reasons")
        return result

    async def generate_reasons_batch(
        self,
        context: StructuredUserContext,
        certificates: list[dict[str, Any]],
    ) -> list[str]:
        """여러 자격증에 대한 추천 이유를 1회 LLM 호출로 생성합니다.

        배치 프롬프트로 모든 자격증을 한 번에 처리하여
        API 호출 횟수와 비용을 대폭 절감합니다.
        (기존: N회 호출 → 변경: 1회 호출)

        Args:
            context: 구조화된 사용자 상황 정보.
            certificates: 자격증 정보 리스트.

        Returns:
            list[str]: 각 자격증에 대한 추천 이유 리스트 (입력 순서 보장).
        """
        default_reasons = [
            (
                f"{cert.get('title', '이 자격증')}은(는) "
                f"{context.goal} 목표에 적합한 자격증입니다."
            )
            for cert in certificates
        ]

        try:
            reason_map = await self._call_llm_batch(context, certificates)
        except Exception as e:
            logger.error(f"[ReasonGenerator] Batch LLM call failed: {e}")
            return default_reasons

        # title 기준으로 순서 매핑, 누락 시 기본 이유
        results = []
        for i, cert in enumerate(certificates):
            title = cert.get("title", "")
            reason = reason_map.get(title)
            if reason and isinstance(reason, str) and reason.strip():
                results.append(reason.strip())
            else:
                logger.warning(
                    f"[ReasonGenerator] Missing reason for '{title}', using default"
                )
                results.append(default_reasons[i])

        return results


# Singleton instance
_reason_generator: Optional[ReasonGeneratorService] = None


def get_reason_generator() -> ReasonGeneratorService:
    """싱글턴 ReasonGeneratorService 인스턴스를 반환합니다."""
    global _reason_generator
    if _reason_generator is None:
        _reason_generator = ReasonGeneratorService()
    return _reason_generator
