"""검색 서비스 팩토리.

이 모듈은 SearXNG 검색 서비스를 생성합니다.

SearXNG은 오픈소스 메타 검색 엔진으로, 무료로 사용할 수 있습니다.

설치:
    docker run -d -p 8888:8080 searxng/searxng

사용 예:
    service = get_search_service()
    results = await service.search_certificate_comprehensive("정보처리기사")
"""

import logging

from app.services.search.protocol import SearchServiceProtocol

logger = logging.getLogger(__name__)


def get_search_service() -> SearchServiceProtocol:
    """검색 서비스를 생성합니다.

    Returns:
        SearXNGSearchService 인스턴스.
    """
    from app.services.search.searxng_search import SearXNGSearchService

    logger.info("검색 서비스 생성: provider=searxng")
    return SearXNGSearchService()


def get_searxng_service() -> SearchServiceProtocol:
    """SearXNG Search 서비스를 반환합니다.

    Returns:
        SearXNGSearchService 인스턴스.
    """
    from app.services.search.searxng_search import get_searxng_service as _get_searxng

    return _get_searxng()
