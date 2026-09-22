"""크롤러 팩토리.

이 모듈은 URL에 따라 적절한 크롤러를 반환하는 팩토리 함수를 제공합니다.
의존성 역전 패턴을 사용하여 크롤러 구현체를 선택합니다.
"""

import logging

from app.services.search.crawler.playwright_crawler import (
    get_playwright_crawler,
    is_playwright_required,
)
from app.services.search.crawler.protocol import CrawlerProtocol
from app.services.search.crawler.trafilatura_crawler import (
    get_trafilatura_crawler,
)

logger = logging.getLogger(__name__)


def get_crawler(crawler_type: str = "trafilatura") -> CrawlerProtocol:
    """지정된 유형의 크롤러를 반환합니다.

    Args:
        crawler_type: 크롤러 유형 ("trafilatura" 또는 "playwright").

    Returns:
        CrawlerProtocol: 요청된 크롤러 인스턴스.

    Raises:
        ValueError: 알 수 없는 크롤러 유형인 경우.
    """
    if crawler_type == "trafilatura":
        return get_trafilatura_crawler()
    elif crawler_type == "playwright":
        return get_playwright_crawler()
    else:
        raise ValueError(f"Unknown crawler type: {crawler_type}")


def get_crawler_for_url(
    url: str,
    *,
    playwright_enabled: bool = True,
) -> CrawlerProtocol:
    """URL에 적합한 크롤러를 반환합니다.

    URL의 특성에 따라 적절한 크롤러를 자동으로 선택합니다:
    - JS 렌더링 사이트 → PlaywrightCrawler (playwright_enabled가 True인 경우)
    - 일반 정적 사이트 → TrafilaturaCrawler

    Args:
        url: 크롤링할 URL.
        playwright_enabled: Playwright 사용 여부 (기본: True).

    Returns:
        CrawlerProtocol: URL에 적합한 크롤러 인스턴스.
    """
    # Playwright가 비활성화되어 있으면 항상 Trafilatura 사용
    if not playwright_enabled:
        return get_trafilatura_crawler()

    # JS 렌더링 사이트인지 확인
    if is_playwright_required(url):
        return get_playwright_crawler()

    # 기본적으로 Trafilatura 사용 (더 빠르고 가벼움)
    return get_trafilatura_crawler()
