"""Recommendation API endpoints.

이 모듈은 사용자 컨텍스트 기반 자격증 추천 API를 제공합니다.
하이브리드 검색(Dense + BM25 Sparse + RRF) 기반 통합 엔드포인트만 활성화.
"""

import logging

from fastapi import APIRouter

from app.api.deps import DBSession
from app.schemas.recommendation import (
    StructuredRecommendationRequest,
    UnifiedRecommendationRequest,
    UnifiedRecommendationResponse,
)
from app.services.study.natural_recommendation_service import (
    NaturalRecommendationService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/unified", response_model=UnifiedRecommendationResponse)
async def get_unified_recommendations(
    request: UnifiedRecommendationRequest,
    db: DBSession,
) -> UnifiedRecommendationResponse:
    """통합 추천 (분야 선택 + 자연어).

    사용자가 관심 분야를 선택하고 자연어로 상황을 설명하면,
    해당 분야 내에서 맞춤형 자격증을 추천합니다.

    3단계 파이프라인:
    1. 규칙 기반 컨텍스트 파싱 (4단계 NLU)
    2. 하이브리드 검색 (Dense + BM25 Sparse + RRF 결합)
    3. 데이터 기반 템플릿 추천 이유 생성

    Args:
        request: 통합 추천 요청 (domains + user_input)
        db: SQLAlchemy 데이터베이스 세션

    Returns:
        UnifiedRecommendationResponse: 추천 결과
    """
    logger.info(
        f"Unified recommendation request: domains={request.domains}, input={request.user_input[:50]}..."
    )

    try:
        service = NaturalRecommendationService(db)
        response = await service.get_unified_recommendations(request)

        logger.info(
            f"Returning {len(response.recommendations)} unified recommendations"
        )
        return response
    except Exception as e:
        logger.error(f"Unified recommendation error: {type(e).__name__}: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


@router.post("/structured", response_model=UnifiedRecommendationResponse)
async def get_structured_recommendations(
    request: StructuredRecommendationRequest,
    db: DBSession,
) -> UnifiedRecommendationResponse:
    """구조화된 입력 기반 추천 (Contextual Retrieval).

    3단계 파이프라인:
    1. 구조화된 입력 → 검색 쿼리 + 메타데이터 필터
    2. 하이브리드 검색 (Dense + BM25 + RRF)
    3. 데이터 기반 템플릿 추천 이유 생성

    Args:
        request: 구조화된 추천 요청 (domains + purpose + current_status)
        db: SQLAlchemy 데이터베이스 세션

    Returns:
        UnifiedRecommendationResponse: 추천 결과
    """
    logger.info(
        f"Structured recommendation request: domains={request.domains}, purpose={request.purpose}"
    )

    try:
        service = NaturalRecommendationService(db)
        response = await service.get_structured_recommendations(request)

        logger.info(
            f"Returning {len(response.recommendations)} structured recommendations"
        )
        return response
    except Exception as e:
        logger.error(f"Structured recommendation error: {type(e).__name__}: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
