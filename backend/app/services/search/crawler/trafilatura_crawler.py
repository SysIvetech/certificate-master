"""Trafilatura 기반 크롤러.

이 모듈은 정적 HTML 페이지에서 본문을 추출하는 크롤러를 구현합니다.
기존 ContentCrawlerService 로직을 리팩토링하여 CrawlerProtocol을 따르도록 합니다.
"""

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

from trafilatura import extract, fetch_url
from trafilatura.metadata import extract_metadata

from app.services.search.crawler.protocol import CrawlResult

logger = logging.getLogger(__name__)


# 크롤링 불가능한 URL 패턴 (파일 다운로드)
_DOWNLOAD_URL_PATTERNS = [
    r"downloadFile\.do",  # moel.go.kr 등
    r"flDownload\.do",  # law.go.kr
    r"download\.do",  # 일반적인 다운로드
    r"getFile\.",  # ulsan.go.kr 등 파일 다운로드
    r"fileDown",  # 일반적인 파일 다운로드
    r"fileId=",  # korea.kr 등
    r"_upload_file_download",  # 게시판 첨부파일
    r"linkDownload",  # 링크 다운로드
    r"download\.9is",  # wanju.go.kr
    r"ResourceOpen\.do",  # bdu.ac.kr
    r"BOARD_ATTACH",  # 대학교 게시판 첨부파일
    r"/download/",  # 일반적인 다운로드 경로
    r"/attach/",  # 첨부파일 경로
    r"/files?/",  # 파일 경로
]

# 크롤링 불가능한 파일 확장자
_NON_HTML_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
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
    ".webp",
    ".mp3",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
}

# 컴파일된 정규식 패턴
_DOWNLOAD_PATTERN = re.compile("|".join(_DOWNLOAD_URL_PATTERNS), re.IGNORECASE)

# JS 렌더링 사이트 목록 (Trafilatura로 처리 불가)
_JS_RENDERED_DOMAINS: set[str] = {
    # 채용 사이트 (SPA/React 기반)
    "m.jobkorea.co.kr",
    "jobkorea.co.kr",
    "m.saramin.co.kr",
    "saramin.co.kr",
    "wanted.co.kr",
    "incruit.com",
    # 소셜/커뮤니티 (SPA)
    "story.kakao.com",
    "brunch.co.kr",
}


def _is_crawlable_url(url: str) -> bool:
    """URL이 크롤링 가능한지 확인합니다."""
    # 다운로드 URL 패턴 확인
    if _DOWNLOAD_PATTERN.search(url):
        return False

    # URL 경로에서 파일 확장자 확인
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext in _NON_HTML_EXTENSIONS:
            if path.endswith(ext):
                return False
    except Exception:
        pass

    return True


def _is_js_rendered_domain(url: str) -> bool:
    """URL이 JS 렌더링 사이트인지 확인합니다."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 정확한 도메인 일치
        if domain in _JS_RENDERED_DOMAINS:
            return True

        # 서브도메인 포함 확인
        for js_domain in _JS_RENDERED_DOMAINS:
            if domain.endswith("." + js_domain):
                return True

        return False

    except Exception:
        return False


class TrafilaturaCrawler:
    """Trafilatura 기반 크롤러.

    정적 HTML 페이지에서 본문 텍스트를 추출합니다.
    JS 렌더링이 필요한 사이트는 처리할 수 없습니다.

    Attributes:
        max_content_length: 추출할 최대 콘텐츠 길이 (기본: 2000자).
        timeout: 요청 타임아웃 초 (기본: 10초).
    """

    def __init__(
        self,
        max_content_length: int = 2000,
        timeout: float = 10.0,
    ):
        """TrafilaturaCrawler를 초기화합니다.

        Args:
            max_content_length: 추출할 최대 콘텐츠 길이.
            timeout: 요청 타임아웃 (초).
        """
        self.max_content_length = max_content_length
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        """크롤러 제공자 이름을 반환합니다."""
        return "trafilatura"

    def can_handle(self, url: str) -> bool:
        """이 크롤러가 해당 URL을 처리할 수 있는지 반환합니다.

        Trafilatura는 정적 HTML만 처리 가능합니다.
        - 파일 다운로드 URL: 불가
        - JS 렌더링 사이트: 불가

        Args:
            url: 확인할 URL.

        Returns:
            bool: 처리 가능하면 True.
        """
        # 파일 다운로드 URL 필터링
        if not _is_crawlable_url(url):
            return False

        # JS 렌더링 사이트 필터링
        if _is_js_rendered_domain(url):
            return False

        return True

    async def extract_content(self, url: str) -> CrawlResult:
        """URL에서 본문 콘텐츠를 추출합니다.

        Args:
            url: 크롤링할 웹 페이지 URL.

        Returns:
            CrawlResult: 추출된 콘텐츠와 메타데이터.
        """
        # 파일 다운로드 URL 필터링
        if not _is_crawlable_url(url):
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    ⏭️  [SKIP] {short_url} (download URL)", flush=True)
            return CrawlResult(
                content="",
                title="",
                success=False,
                method=self.provider_name,
                url=url,
                error="Skipped: File download URL (not HTML)",
            )

        # JS 렌더링 사이트 필터링
        if _is_js_rendered_domain(url):
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    ⏭️  [SKIP] {short_url} (JS-rendered site)", flush=True)
            return CrawlResult(
                content="",
                title="",
                success=False,
                method=self.provider_name,
                url=url,
                error="Skipped: JS-rendered site (use Playwright instead)",
            )

        try:
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    🔗 [FETCH] {short_url}", flush=True)

            # 비동기 컨텍스트에서 동기 함수 실행
            loop = asyncio.get_event_loop()

            # fetch_url 실행
            downloaded = await loop.run_in_executor(None, lambda: fetch_url(url))

            if not downloaded:
                error_msg = "Connection failed or empty response"
                print(f"    ❌ [ERROR] {error_msg}", flush=True)
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method=self.provider_name,
                    url=url,
                    error=error_msg,
                )

            # 본문 추출
            content = await loop.run_in_executor(
                None,
                lambda: extract(
                    downloaded,
                    favor_precision=True,
                    include_formatting=True,
                    include_tables=True,
                    include_comments=False,
                    deduplicate=True,
                    target_language="ko",
                    no_fallback=False,
                ),
            )

            if not content:
                error_msg = "No text content extracted"
                print(f"    ⚠️  [WARN] {error_msg}", flush=True)
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method=self.provider_name,
                    url=url,
                    error=error_msg,
                )

            # 메타데이터 추출
            metadata = await loop.run_in_executor(
                None, lambda: extract_metadata(downloaded)
            )
            title = metadata.title if metadata and metadata.title else ""

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
                title=title,
                success=True,
                method=self.provider_name,
                url=url,
                error=None,
            )

        except Exception as e:
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)[:100]}"
            print(f"    ❌ [ERROR] {error_msg}", flush=True)
            logger.debug(f"Crawl exception for {url}: {e}")
            return CrawlResult(
                content="",
                title="",
                success=False,
                method=self.provider_name,
                url=url,
                error=error_msg,
            )


# 싱글턴 인스턴스
_trafilatura_crawler: Optional[TrafilaturaCrawler] = None


def get_trafilatura_crawler() -> TrafilaturaCrawler:
    """싱글턴 TrafilaturaCrawler 인스턴스를 반환합니다."""
    global _trafilatura_crawler
    if _trafilatura_crawler is None:
        _trafilatura_crawler = TrafilaturaCrawler()
    return _trafilatura_crawler
