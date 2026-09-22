"""Playwright 기반 크롤러.

이 모듈은 JavaScript 렌더링이 필요한 페이지에서 본문을 추출하는 크롤러를 구현합니다.
채용 사이트(jobkorea, saramin 등) 및 SPA 기반 사이트를 지원합니다.
"""

import logging
import re
from typing import Optional
from urllib.parse import urlparse

from app.services.search.crawler.protocol import CrawlResult

logger = logging.getLogger(__name__)


# Playwright가 필요한 도메인 목록
# 이 도메인들은 JS 렌더링 없이는 콘텐츠를 추출할 수 없습니다.
PLAYWRIGHT_REQUIRED_DOMAINS: set[str] = {
    # 채용 사이트 (SPA/React 기반)
    "jobkorea.co.kr",
    "saramin.co.kr",
    "wanted.co.kr",
    "incruit.com",
    # 소셜/커뮤니티 (SPA)
    "story.kakao.com",
    "brunch.co.kr",
    # 공식 사이트 (일부 동적 콘텐츠)
    "q-net.or.kr",
}


def _is_playwright_domain(url: str) -> bool:
    """URL이 Playwright가 필요한 도메인인지 확인합니다."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 모바일 서브도메인 제거 (m.jobkorea.co.kr -> jobkorea.co.kr)
        if domain.startswith("m."):
            domain = domain[2:]

        # 정확한 도메인 일치
        if domain in PLAYWRIGHT_REQUIRED_DOMAINS:
            return True

        # 서브도메인 포함 확인
        for pw_domain in PLAYWRIGHT_REQUIRED_DOMAINS:
            if domain.endswith("." + pw_domain):
                return True

        return False

    except Exception:
        return False


class PlaywrightCrawler:
    """Playwright 기반 크롤러.

    JavaScript 렌더링이 필요한 페이지에서 본문 텍스트를 추출합니다.
    헤드리스 브라우저를 사용하여 완전히 렌더링된 페이지에서 콘텐츠를 추출합니다.

    Attributes:
        max_content_length: 추출할 최대 콘텐츠 길이 (기본: 2000자).
        timeout: 페이지 로드 타임아웃 밀리초 (기본: 30000ms).
        headless: 헤드리스 모드 사용 여부 (기본: True).
    """

    def __init__(
        self,
        max_content_length: int = 2000,
        timeout: float = 30.0,
        headless: bool = True,
    ):
        """PlaywrightCrawler를 초기화합니다.

        Args:
            max_content_length: 추출할 최대 콘텐츠 길이.
            timeout: 페이지 로드 타임아웃 (초).
            headless: 헤드리스 모드 사용 여부.
        """
        self.max_content_length = max_content_length
        self.timeout = timeout * 1000  # 밀리초로 변환
        self.headless = headless
        self._playwright = None
        self._browser = None

    @property
    def provider_name(self) -> str:
        """크롤러 제공자 이름을 반환합니다."""
        return "playwright"

    def can_handle(self, url: str) -> bool:
        """이 크롤러가 해당 URL을 처리할 수 있는지 반환합니다.

        Playwright는 모든 웹 페이지를 처리할 수 있습니다.
        특히 JS 렌더링이 필요한 사이트에 적합합니다.

        Args:
            url: 확인할 URL.

        Returns:
            bool: 항상 True (모든 웹 페이지 처리 가능).
        """
        # Playwright는 모든 웹 페이지를 처리할 수 있음
        # 단, PDF 등 파일 다운로드 URL은 제외
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()

            # 비-HTML 파일 확장자 체크
            non_html_extensions = {
                ".pdf",
                ".hwp",
                ".doc",
                ".docx",
                ".xls",
                ".xlsx",
                ".zip",
                ".rar",
                ".7z",
                ".tar",
                ".gz",
                ".jpg",
                ".jpeg",
                ".png",
                ".gif",
                ".bmp",
                ".mp3",
                ".mp4",
                ".avi",
                ".mov",
            }

            for ext in non_html_extensions:
                if path.endswith(ext):
                    return False

            return True

        except Exception:
            return True

    async def _ensure_browser(self):
        """브라우저 인스턴스가 준비되었는지 확인합니다."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless
                )
            except ImportError:
                logger.warning(
                    "Playwright not installed. Install with: pip install playwright && playwright install chromium"
                )
                raise ImportError("Playwright is not installed")

    async def _cleanup(self):
        """브라우저 리소스를 정리합니다."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def extract_content(self, url: str) -> CrawlResult:
        """URL에서 본문 콘텐츠를 추출합니다.

        Playwright를 사용하여 JS 렌더링 후 콘텐츠를 추출합니다.

        Args:
            url: 크롤링할 웹 페이지 URL.

        Returns:
            CrawlResult: 추출된 콘텐츠와 메타데이터.
        """
        short_url = url[:60] + "..." if len(url) > 60 else url

        try:
            print(f"    🎭 [PLAYWRIGHT] {short_url}", flush=True)

            await self._ensure_browser()

            # 새 페이지 생성
            page = await self._browser.new_page()

            try:
                # 페이지 로드
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)

                # 추가 대기 (동적 콘텐츠 로딩)
                await page.wait_for_timeout(1000)

                # 페이지 제목 추출
                title = await page.title()

                # 본문 콘텐츠 추출 (여러 선택자 시도)
                content = ""

                # 주요 콘텐츠 영역 선택자 (우선순위순)
                selectors = [
                    "article",
                    "main",
                    "[role='main']",
                    ".content",
                    ".article",
                    ".post-content",
                    "#content",
                    "#main",
                    "body",
                ]

                for selector in selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            content = await element.inner_text()
                            if content and len(content.strip()) > 100:
                                break
                    except Exception:
                        continue

                # 콘텐츠가 없으면 전체 페이지 텍스트 추출
                if not content or len(content.strip()) < 100:
                    content = await page.inner_text("body")

                # 콘텐츠 정리
                if content:
                    # 연속된 공백/줄바꿈 정리
                    content = re.sub(r"\n{3,}", "\n\n", content)
                    content = re.sub(r"[ \t]+", " ", content)
                    content = content.strip()

                if not content:
                    error_msg = "No text content extracted"
                    print(f"    ⚠️  [WARN] {error_msg}", flush=True)
                    return CrawlResult(
                        content="",
                        title=title or "",
                        success=False,
                        method=self.provider_name,
                        url=url,
                        error=error_msg,
                    )

                print(f"    ✅ [OK] {len(content)}자 추출", flush=True)

                # 콘텐츠 길이 제한
                if len(content) > self.max_content_length:
                    truncated = content[: self.max_content_length - 3]
                    last_period = truncated.rfind(".")
                    if last_period > (self.max_content_length - 3) * 0.7:
                        content = truncated[: last_period + 1]
                    else:
                        content = truncated + "..."

                return CrawlResult(
                    content=content,
                    title=title or "",
                    success=True,
                    method=self.provider_name,
                    url=url,
                    error=None,
                )

            finally:
                await page.close()

        except ImportError:
            error_msg = "Playwright not installed"
            print(f"    ❌ [ERROR] {error_msg}", flush=True)
            return CrawlResult(
                content="",
                title="",
                success=False,
                method=self.provider_name,
                url=url,
                error=error_msg,
            )

        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)[:100]}"
            print(f"    ❌ [ERROR] {error_msg}", flush=True)
            logger.debug(f"Playwright crawl exception for {url}: {e}")
            return CrawlResult(
                content="",
                title="",
                success=False,
                method=self.provider_name,
                url=url,
                error=error_msg,
            )


# 싱글턴 인스턴스
_playwright_crawler: Optional[PlaywrightCrawler] = None


def get_playwright_crawler() -> PlaywrightCrawler:
    """싱글턴 PlaywrightCrawler 인스턴스를 반환합니다."""
    global _playwright_crawler
    if _playwright_crawler is None:
        _playwright_crawler = PlaywrightCrawler()
    return _playwright_crawler


def is_playwright_required(url: str) -> bool:
    """URL이 Playwright가 필요한지 확인합니다.

    Args:
        url: 확인할 URL.

    Returns:
        bool: Playwright가 필요하면 True.
    """
    return _is_playwright_domain(url)
