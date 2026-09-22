"""임베딩 서비스 팩토리.

이 모듈은 OpenAI 기반 임베딩 서비스를 생성합니다.

사용 예:
    service = get_embedding_service()
"""

import logging

from app.services.embedding.protocol import EmbeddingServiceProtocol

logger = logging.getLogger(__name__)


def get_embedding_service() -> EmbeddingServiceProtocol:
    """OpenAI 임베딩 서비스를 생성합니다.

    Returns:
        EmbeddingServiceProtocol 구현체.
    """
    logger.info("임베딩 서비스 생성: provider=openai")

    from app.services.embedding.service import EmbeddingService

    return EmbeddingService()
