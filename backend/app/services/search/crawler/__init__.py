"""크롤러 서비스 패키지.

이 패키지는 웹 페이지 콘텐츠 크롤링을 위한 다양한 크롤러 구현체를 제공합니다:
- TrafilaturaCrawler: 정적 HTML 페이지용 (기본)
- PlaywrightCrawler: JS 렌더링 페이지용 (채용사이트 등)
- SmartCrawler: 지능적 크롤러 선택 (권장)
"""

from app.services.search.crawler.factory import get_crawler, get_crawler_for_url
from app.services.search.crawler.protocol import CrawlerProtocol, CrawlResult
from app.services.search.crawler.smart_crawler import (
    CrawlerMetrics,
    SmartCrawler,
    get_smart_crawler,
)

__all__ = [
    "CrawlerProtocol",
    "CrawlResult",
    "get_crawler",
    "get_crawler_for_url",
    "SmartCrawler",
    "get_smart_crawler",
    "CrawlerMetrics",
]
