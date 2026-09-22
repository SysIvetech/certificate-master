"""검색 서비스 모듈.

- SearchServiceProtocol: 검색 서비스 프로토콜
- get_search_service: 검색 서비스 팩토리
- SearXNGSearchService: SearXNG 검색 서비스 (기본)
- ContentCrawlerService: 웹 콘텐츠 크롤러
"""

from .content_crawler import ContentCrawlerService
from .factory import get_search_service
from .protocol import SearchServiceProtocol
from .searxng_search import SearXNGSearchService

__all__ = [
    "SearchServiceProtocol",
    "get_search_service",
    "SearXNGSearchService",
    "ContentCrawlerService",
]
