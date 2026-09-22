"""Playwright 브라우저 풀 관리.

이 모듈은 Playwright 브라우저 인스턴스를 효율적으로 관리합니다.
동시 페이지 수를 제한하여 메모리 사용을 최적화합니다.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


class BrowserPool:
    """Playwright 브라우저 인스턴스 풀.

    브라우저와 페이지 인스턴스를 관리하여 리소스를 효율적으로 사용합니다.
    세마포어를 사용하여 동시 페이지 수를 제한합니다.

    Attributes:
        max_browsers: 최대 브라우저 인스턴스 수 (기본: 2).
        max_pages_per_browser: 브라우저당 최대 페이지 수 (기본: 5).
        headless: 헤드리스 모드 사용 여부 (기본: True).
        timeout: 기본 타임아웃 초 (기본: 30.0).
    """

    def __init__(
        self,
        max_browsers: int = 2,
        max_pages_per_browser: int = 5,
        headless: bool = True,
        timeout: float = 30.0,
    ):
        """BrowserPool을 초기화합니다.

        Args:
            max_browsers: 최대 브라우저 인스턴스 수.
            max_pages_per_browser: 브라우저당 최대 페이지 수.
            headless: 헤드리스 모드 사용 여부.
            timeout: 기본 타임아웃 (초).
        """
        self.max_browsers = max_browsers
        self.max_pages_per_browser = max_pages_per_browser
        self.headless = headless
        self.timeout = timeout

        # 동시성 제어
        self._semaphore = asyncio.Semaphore(self.max_concurrent)

        # 브라우저 인스턴스
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()

    @property
    def max_concurrent(self) -> int:
        """최대 동시 페이지 수를 반환합니다."""
        return self.max_browsers * self.max_pages_per_browser

    async def _ensure_browser(self):
        """브라우저 인스턴스가 준비되었는지 확인합니다."""
        if self._browser is None:
            async with self._lock:
                if self._browser is None:
                    try:
                        from playwright.async_api import async_playwright

                        self._playwright = await async_playwright().start()
                        self._browser = await self._playwright.chromium.launch(
                            headless=self.headless
                        )
                        logger.info("Browser pool: Browser launched")
                    except ImportError:
                        logger.warning(
                            "Playwright not installed. "
                            "Install with: pip install playwright && playwright install chromium"
                        )
                        raise

    @asynccontextmanager
    async def get_page(self) -> AsyncGenerator:
        """새 페이지를 생성하여 반환합니다.

        세마포어를 사용하여 동시 페이지 수를 제한합니다.
        컨텍스트 매니저로 사용하여 자동으로 페이지를 닫습니다.

        Yields:
            Page: Playwright 페이지 인스턴스.

        Raises:
            ImportError: Playwright가 설치되지 않은 경우.

        Example:
            async with pool.get_page() as page:
                await page.goto("https://example.com")
                content = await page.content()
        """
        async with self._semaphore:
            await self._ensure_browser()

            page = await self._browser.new_page()
            page.set_default_timeout(self.timeout * 1000)

            try:
                yield page
            finally:
                await page.close()

    async def cleanup(self):
        """브라우저 리소스를 정리합니다.

        브라우저와 Playwright 인스턴스를 종료합니다.
        """
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                    logger.info("Browser pool: Browser closed")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                finally:
                    self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                    logger.info("Browser pool: Playwright stopped")
                except Exception as e:
                    logger.warning(f"Error stopping playwright: {e}")
                finally:
                    self._playwright = None


# 싱글턴 인스턴스
_browser_pool: Optional[BrowserPool] = None


def get_browser_pool() -> BrowserPool:
    """싱글턴 BrowserPool 인스턴스를 반환합니다.

    Returns:
        BrowserPool 인스턴스.
    """
    global _browser_pool
    if _browser_pool is None:
        _browser_pool = BrowserPool()
    return _browser_pool


def reset_browser_pool():
    """싱글턴 BrowserPool을 리셋합니다.

    테스트 또는 재시작 시 사용합니다.
    """
    global _browser_pool
    _browser_pool = None
