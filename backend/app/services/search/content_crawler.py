"""웹 페이지 콘텐츠 크롤링 서비스.

이 모듈은 검색 결과 URL에서 실제 페이지 본문을 추출하여
LLM에 더 풍부한 컨텍스트를 제공합니다.

주요 기능:
- Trafilatura를 사용한 본문 추출
- 병렬 크롤링 지원
- 콘텐츠 길이 제한
- 파일 다운로드 URL 필터링
- JS 렌더링 사이트 사전 감지 (크롤링 스킵)
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

from trafilatura import extract, fetch_url
from trafilatura.metadata import extract_metadata

logger = logging.getLogger(__name__)


# 크롤링 불가능한 URL 패턴 (파일 다운로드)
_DOWNLOAD_URL_PATTERNS = [
    r"downloadFile\.do",  # moel.go.kr 등
    r"flDownload\.do",  # law.go.kr
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


def is_crawlable_url(url: str) -> bool:
    """URL이 크롤링 가능한지 확인합니다.

    파일 다운로드 URL이나 비-HTML 파일 확장자를 가진 URL은
    크롤링 대상에서 제외합니다.

    Args:
        url: 확인할 URL.

    Returns:
        bool: 크롤링 가능하면 True, 불가능하면 False.
    """
    # 다운로드 URL 패턴 확인
    if _DOWNLOAD_PATTERN.search(url):
        return False

    # URL 경로에서 파일 확장자 확인
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()

        # 경로의 마지막 부분에서 확장자 추출
        for ext in _NON_HTML_EXTENSIONS:
            if path.endswith(ext):
                return False
    except Exception:
        pass

    return True


@dataclass
class CrawlResult:
    """크롤링 결과를 담는 데이터 클래스.

    Attributes:
        content: 추출된 본문 콘텐츠.
        title: 페이지 제목.
        success: 크롤링 성공 여부.
        method: 사용된 추출 방법 (trafilatura).
        error: 실패 시 에러 메시지.
    """

    content: str
    title: str
    success: bool
    method: str
    error: Optional[str] = None


class ContentCrawlerService:
    """웹 페이지 콘텐츠를 추출하는 서비스.

    Trafilatura 라이브러리를 사용하여 웹 페이지에서
    본문 텍스트를 추출합니다.

    Attributes:
        max_content_length: 추출할 최대 콘텐츠 길이 (기본: 2000자).
        timeout: 요청 타임아웃 초 (기본: 10초).
        max_concurrent: 동시 크롤링 수 (기본: 5개).
    """

    def __init__(
        self,
        max_content_length: int = 2000,
        timeout: float = 10.0,
        max_concurrent: int = 5,
    ):
        """ContentCrawlerService를 초기화합니다.

        Args:
            max_content_length: 추출할 최대 콘텐츠 길이.
            timeout: 요청 타임아웃 (초).
            max_concurrent: 동시 크롤링 최대 수.
        """
        self.max_content_length = max_content_length
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """동시 요청 제한을 위한 세마포어를 반환합니다."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def extract_content(self, url: str) -> CrawlResult:
        """URL에서 본문 콘텐츠를 추출합니다.

        Args:
            url: 크롤링할 웹 페이지 URL.

        Returns:
            CrawlResult: 추출된 콘텐츠와 메타데이터.
        """
        import sys

        from app.services.search.url_filter import is_js_rendered_domain

        # 파일 다운로드 URL 필터링 (크롤링 시도 전에 스킵)
        if not is_crawlable_url(url):
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    ⏭️  [SKIP] {short_url} (download URL)")
            sys.stdout.flush()
            return CrawlResult(
                content="",
                title="",
                success=False,
                method="trafilatura",
                error="Skipped: File download URL (not HTML)",
            )

        # JS 렌더링 사이트 필터링 (크롤링 시도 없이 바로 snippet fallback 유도)
        if is_js_rendered_domain(url):
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    ⏭️  [SKIP] {short_url} (JS-rendered site)")
            sys.stdout.flush()
            return CrawlResult(
                content="",
                title="",
                success=False,
                method="trafilatura",
                error="Skipped: JS-rendered site (use snippet fallback)",
            )

        try:
            # URL 짧게 표시
            short_url = url[:60] + "..." if len(url) > 60 else url
            print(f"    🔗 [FETCH] {short_url}")
            sys.stdout.flush()

            # 비동기 컨텍스트에서 동기 함수 실행
            loop = asyncio.get_event_loop()

            # fetch_url 실행 (동기 함수를 executor에서 실행)
            downloaded = await loop.run_in_executor(None, lambda: fetch_url(url))

            if not downloaded:
                error_msg = (
                    "Connection failed or empty response (possible SSL/timeout/404)"
                )
                print(f"    ❌ [ERROR] {error_msg}")
                sys.stdout.flush()
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method="trafilatura",
                    error=error_msg,
                )

            # 본문 추출 (Context7 Trafilatura 문서 기반 최적화)
            # - favor_precision: 정확한 본문만 추출 (노이즈 감소)
            # - include_formatting: 제목/리스트 등 구조 유지
            # - include_tables: 시험 일정/배점 테이블 유지
            # - deduplicate: 중복 문단 제거
            # - target_language: 한국어 콘텐츠 우선
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
                error_msg = "No text content extracted (JS-rendered or non-text page)"
                print(f"    ⚠️  [WARN] {error_msg}")
                sys.stdout.flush()
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method="trafilatura",
                    error=error_msg,
                )

            # 메타데이터 추출 (제목)
            metadata = await loop.run_in_executor(
                None, lambda: extract_metadata(downloaded)
            )
            title = metadata.title if metadata and metadata.title else ""

            print(f"    ✅ [OK] {len(content)}자 추출")
            sys.stdout.flush()

            # 콘텐츠 길이 제한
            if len(content) > self.max_content_length:
                # 문장 단위로 자르기 시도
                truncated = content[: self.max_content_length - 3]  # "..." 공간 확보
                # 마지막 완전한 문장까지만 포함
                last_period = truncated.rfind(".")
                if last_period > (self.max_content_length - 3) * 0.7:
                    content = truncated[: last_period + 1]
                else:
                    content = truncated + "..."

            return CrawlResult(
                content=content,
                title=title,
                success=True,
                method="trafilatura",
                error=None,
            )

        except Exception as e:
            short_url = url[:60] + "..." if len(url) > 60 else url
            error_type = type(e).__name__
            error_msg = f"{error_type}: {str(e)[:100]}"
            print(f"    ❌ [ERROR] {error_msg}")
            sys.stdout.flush()
            logger.debug(f"Crawl exception for {url}: {e}")
            return CrawlResult(
                content="",
                title="",
                success=False,
                method="trafilatura",
                error=error_msg,
            )

    async def extract_multiple(self, urls: List[str]) -> List[CrawlResult]:
        """여러 URL을 병렬로 크롤링합니다.

        Args:
            urls: 크롤링할 URL 목록.

        Returns:
            List[CrawlResult]: 각 URL의 크롤링 결과 목록.
        """
        semaphore = self._get_semaphore()

        async def crawl_with_limit(url: str) -> CrawlResult:
            async with semaphore:
                return await self.extract_content(url)

        tasks = [crawl_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 예외를 CrawlResult로 변환
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    CrawlResult(
                        content="",
                        title="",
                        success=False,
                        method="trafilatura",
                        error=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results


# 싱글턴 인스턴스
_crawler_service: Optional[ContentCrawlerService] = None


def get_content_crawler() -> ContentCrawlerService:
    """싱글턴 ContentCrawlerService 인스턴스를 반환합니다.

    Returns:
        ContentCrawlerService 인스턴스.
    """
    global _crawler_service
    if _crawler_service is None:
        _crawler_service = ContentCrawlerService()
    return _crawler_service
