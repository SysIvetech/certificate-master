"""지능적 크롤러 선택 및 통합.

이 모듈은 URL 특성에 따라 적절한 크롤러를 자동으로 선택합니다.
- 일반 사이트: Trafilatura (빠르고 가벼움)
- JS 렌더링 사이트: Playwright (headless browser)
- Trafilatura 실패 시: Playwright fallback
"""

import logging
from dataclasses import dataclass
from typing import Optional

from app.services.search.crawler.playwright_crawler import (
    PlaywrightCrawler,
    is_playwright_required,
)
from app.services.search.crawler.protocol import CrawlerProtocol, CrawlResult
from app.services.search.crawler.trafilatura_crawler import (
    TrafilaturaCrawler,
)

logger = logging.getLogger(__name__)


@dataclass
class CrawlerMetrics:
    """크롤링 메트릭을 추적하는 데이터 클래스.

    Attributes:
        total_requests: 총 크롤링 요청 수.
        trafilatura_success: Trafilatura 성공 횟수.
        playwright_success: Playwright 성공 횟수.
        fallback_count: Playwright fallback 횟수.
        failed_count: 실패 횟수.
    """

    total_requests: int = 0
    trafilatura_success: int = 0
    playwright_success: int = 0
    fallback_count: int = 0
    failed_count: int = 0

    def reset(self):
        """메트릭을 리셋합니다."""
        self.total_requests = 0
        self.trafilatura_success = 0
        self.playwright_success = 0
        self.fallback_count = 0
        self.failed_count = 0

    def summary(self) -> dict:
        """메트릭 요약을 반환합니다."""
        return {
            "total_requests": self.total_requests,
            "trafilatura_success": self.trafilatura_success,
            "playwright_success": self.playwright_success,
            "fallback_count": self.fallback_count,
            "failed_count": self.failed_count,
            "success_rate": (
                (self.trafilatura_success + self.playwright_success)
                / self.total_requests
                if self.total_requests > 0
                else 0.0
            ),
        }


class SmartCrawler:
    """지능적 크롤러 선택기.

    URL 특성에 따라 적절한 크롤러를 자동으로 선택하고,
    Trafilatura 실패 시 Playwright로 fallback합니다.

    Attributes:
        playwright_enabled: Playwright 사용 여부.
        fallback_enabled: Trafilatura 실패 시 Playwright fallback 여부.
        metrics: 크롤링 메트릭.
    """

    def __init__(
        self,
        playwright_enabled: bool = True,
        fallback_enabled: bool = True,
        max_content_length: int = 2000,
        timeout: float = 30.0,
    ):
        """SmartCrawler를 초기화합니다.

        Args:
            playwright_enabled: Playwright 사용 여부.
            fallback_enabled: Trafilatura 실패 시 Playwright fallback 여부.
            max_content_length: 추출할 최대 콘텐츠 길이.
            timeout: 요청 타임아웃 (초).
        """
        self.playwright_enabled = playwright_enabled
        self.fallback_enabled = fallback_enabled
        self.max_content_length = max_content_length
        self.timeout = timeout

        # 크롤러 인스턴스 (lazy initialization)
        self._trafilatura_crawler: Optional[TrafilaturaCrawler] = None
        self._playwright_crawler: Optional[PlaywrightCrawler] = None

        # 메트릭
        self.metrics = CrawlerMetrics()

    @property
    def provider_name(self) -> str:
        """크롤러 제공자 이름을 반환합니다."""
        return "smart"

    def _get_trafilatura_crawler(self) -> TrafilaturaCrawler:
        """Trafilatura 크롤러를 반환합니다 (lazy initialization)."""
        if self._trafilatura_crawler is None:
            self._trafilatura_crawler = TrafilaturaCrawler(
                max_content_length=self.max_content_length,
                timeout=self.timeout,
            )
        return self._trafilatura_crawler

    def _get_playwright_crawler(self) -> PlaywrightCrawler:
        """Playwright 크롤러를 반환합니다 (lazy initialization)."""
        if self._playwright_crawler is None:
            self._playwright_crawler = PlaywrightCrawler(
                max_content_length=self.max_content_length,
                timeout=self.timeout,
            )
        return self._playwright_crawler

    def _select_crawler(self, url: str) -> CrawlerProtocol:
        """URL에 적합한 크롤러를 선택합니다.

        Args:
            url: 크롤링할 URL.

        Returns:
            선택된 크롤러 인스턴스.
        """
        # Playwright가 비활성화되면 항상 Trafilatura
        if not self.playwright_enabled:
            return self._get_trafilatura_crawler()

        # JS 렌더링 사이트는 Playwright
        if is_playwright_required(url):
            return self._get_playwright_crawler()

        # 기본적으로 Trafilatura (더 빠름)
        return self._get_trafilatura_crawler()

    async def extract_content(self, url: str) -> CrawlResult:
        """URL에서 본문 콘텐츠를 추출합니다.

        지능적으로 크롤러를 선택하고, 실패 시 fallback을 시도합니다.

        Args:
            url: 크롤링할 웹 페이지 URL.

        Returns:
            CrawlResult: 추출된 콘텐츠와 메타데이터.
        """
        self.metrics.total_requests += 1

        # 1. 적절한 크롤러 선택
        self._select_crawler(url)
        is_js_site = is_playwright_required(url)

        # 2. JS 사이트인 경우 바로 Playwright 사용
        if is_js_site and self.playwright_enabled:
            try:
                result = await self._get_playwright_crawler().extract_content(url)
                if result.success:
                    self.metrics.playwright_success += 1
                    return result
            except ImportError as e:
                logger.warning(f"Playwright not available: {e}")
                self.metrics.failed_count += 1
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method="playwright",
                    url=url,
                    error=f"Playwright not installed: {e}",
                )
            except Exception as e:
                logger.error(f"Playwright error for {url}: {e}")

        # 3. Trafilatura로 시도
        trafilatura = self._get_trafilatura_crawler()
        if trafilatura.can_handle(url):
            result = await trafilatura.extract_content(url)

            if result.success:
                self.metrics.trafilatura_success += 1
                return result

            # 4. Trafilatura 실패 시 Playwright fallback
            if self.fallback_enabled and self.playwright_enabled:
                logger.info(
                    f"Trafilatura failed, trying Playwright fallback: {url[:50]}"
                )
                self.metrics.fallback_count += 1

                try:
                    pw_result = await self._get_playwright_crawler().extract_content(
                        url
                    )
                    if pw_result.success:
                        self.metrics.playwright_success += 1
                        return pw_result
                except ImportError as e:
                    logger.warning(f"Playwright fallback not available: {e}")
                    self.metrics.failed_count += 1
                    return CrawlResult(
                        content="",
                        title="",
                        success=False,
                        method="smart",
                        url=url,
                        error=f"Playwright not installed: {e}",
                    )
                except Exception as e:
                    logger.error(f"Playwright fallback error: {e}")

            # Fallback도 실패
            self.metrics.failed_count += 1
            return result

        # Trafilatura가 처리할 수 없는 URL
        self.metrics.failed_count += 1
        return CrawlResult(
            content="",
            title="",
            success=False,
            method="smart",
            url=url,
            error="URL cannot be handled by any crawler",
        )

    def can_handle(self, url: str) -> bool:
        """이 크롤러가 해당 URL을 처리할 수 있는지 반환합니다.

        SmartCrawler는 대부분의 URL을 처리할 수 있습니다.

        Args:
            url: 확인할 URL.

        Returns:
            bool: 처리 가능하면 True.
        """
        # 파일 다운로드 URL은 제외
        trafilatura = self._get_trafilatura_crawler()
        if trafilatura.can_handle(url):
            return True

        # Playwright가 활성화되어 있으면 JS 사이트도 처리 가능
        if self.playwright_enabled:
            playwright = self._get_playwright_crawler()
            return playwright.can_handle(url)

        return False

    def get_metrics_summary(self) -> dict:
        """메트릭 요약을 반환합니다."""
        return self.metrics.summary()

    def reset_metrics(self):
        """메트릭을 리셋합니다."""
        self.metrics.reset()


# 싱글턴 인스턴스
_smart_crawler: Optional[SmartCrawler] = None


def get_smart_crawler() -> SmartCrawler:
    """싱글턴 SmartCrawler 인스턴스를 반환합니다.

    Returns:
        SmartCrawler 인스턴스.
    """
    global _smart_crawler
    if _smart_crawler is None:
        _smart_crawler = SmartCrawler()
    return _smart_crawler


def reset_smart_crawler():
    """싱글턴 SmartCrawler를 리셋합니다.

    테스트 또는 재설정 시 사용합니다.
    """
    global _smart_crawler
    _smart_crawler = None
