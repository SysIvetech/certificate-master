"""SmartCrawler 통합 테스트.

이 모듈은 지능적 크롤러 선택 로직을 테스트합니다.
Trafilatura를 우선 사용하고, JS 사이트는 Playwright로 fallback합니다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSmartCrawlerBasic:
    """SmartCrawler 기본 기능 테스트."""

    def test_smart_crawler_can_be_imported(self):
        """SmartCrawler를 임포트할 수 있어야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        assert SmartCrawler is not None

    def test_smart_crawler_initialization(self):
        """SmartCrawler가 올바르게 초기화되어야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()

        assert crawler.provider_name == "smart"
        assert hasattr(crawler, "playwright_enabled")

    def test_smart_crawler_has_extract_content(self):
        """SmartCrawler에 extract_content 메서드가 있어야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()

        assert hasattr(crawler, "extract_content")
        assert callable(crawler.extract_content)


class TestSmartCrawlerSelection:
    """크롤러 선택 로직 테스트."""

    def test_selects_trafilatura_for_regular_sites(self):
        """일반 사이트에는 Trafilatura를 선택해야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()

        selected = crawler._select_crawler("https://blog.naver.com/abc")
        assert selected.provider_name == "trafilatura"

    def test_selects_playwright_for_js_sites(self):
        """JS 사이트에는 Playwright를 선택해야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler(playwright_enabled=True)

        selected = crawler._select_crawler("https://www.jobkorea.co.kr/job/123")
        assert selected.provider_name == "playwright"

    def test_falls_back_to_trafilatura_when_playwright_disabled(self):
        """Playwright가 비활성화되면 항상 Trafilatura를 사용해야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler(playwright_enabled=False)

        selected = crawler._select_crawler("https://www.jobkorea.co.kr/job/123")
        assert selected.provider_name == "trafilatura"


class TestSmartCrawlerExtract:
    """extract_content 메서드 테스트."""

    @pytest.mark.asyncio
    async def test_extract_content_uses_trafilatura_first(self):
        """extract_content가 Trafilatura를 우선 사용해야 합니다."""
        from app.services.search.crawler.protocol import CrawlResult
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()

        # Trafilatura 크롤러 mock
        mock_result = CrawlResult(
            content="테스트 콘텐츠",
            title="테스트 제목",
            success=True,
            method="trafilatura",
            url="https://example.com",
        )

        with patch.object(crawler, "_trafilatura_crawler") as mock_traf:
            mock_traf.extract_content = AsyncMock(return_value=mock_result)
            mock_traf.can_handle = MagicMock(return_value=True)

            result = await crawler.extract_content("https://example.com")

            mock_traf.extract_content.assert_called_once()
            assert result.success is True
            assert result.method == "trafilatura"

    @pytest.mark.asyncio
    async def test_extract_content_falls_back_to_playwright(self):
        """Trafilatura 실패 시 Playwright로 fallback해야 합니다."""
        from app.services.search.crawler.protocol import CrawlResult
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler(playwright_enabled=True)

        # Trafilatura 실패
        traf_result = CrawlResult(
            content="",
            title="",
            success=False,
            method="trafilatura",
            url="https://example.com",
            error="JS-rendered site",
        )

        # Playwright 성공
        pw_result = CrawlResult(
            content="Playwright 콘텐츠",
            title="Playwright 제목",
            success=True,
            method="playwright",
            url="https://example.com",
        )

        with patch.object(crawler, "_trafilatura_crawler") as mock_traf:
            with patch.object(crawler, "_playwright_crawler") as mock_pw:
                mock_traf.extract_content = AsyncMock(return_value=traf_result)
                mock_traf.can_handle = MagicMock(return_value=True)
                mock_pw.extract_content = AsyncMock(return_value=pw_result)

                result = await crawler.extract_content("https://example.com")

                # Playwright fallback이 호출되었는지 확인
                mock_pw.extract_content.assert_called_once()
                assert result.success is True
                assert result.method == "playwright"


class TestSmartCrawlerMetrics:
    """크롤링 메트릭 테스트."""

    def test_metrics_are_tracked(self):
        """크롤링 메트릭이 추적되어야 합니다."""
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()

        assert hasattr(crawler, "metrics")
        assert hasattr(crawler.metrics, "total_requests")
        assert hasattr(crawler.metrics, "trafilatura_success")
        assert hasattr(crawler.metrics, "playwright_success")
        assert hasattr(crawler.metrics, "fallback_count")

    @pytest.mark.asyncio
    async def test_metrics_increment_on_success(self):
        """성공 시 메트릭이 증가해야 합니다."""
        from app.services.search.crawler.protocol import CrawlResult
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler()
        initial_total = crawler.metrics.total_requests

        mock_result = CrawlResult(
            content="테스트",
            title="제목",
            success=True,
            method="trafilatura",
            url="https://example.com",
        )

        with patch.object(crawler, "_trafilatura_crawler") as mock_traf:
            mock_traf.extract_content = AsyncMock(return_value=mock_result)
            mock_traf.can_handle = MagicMock(return_value=True)

            await crawler.extract_content("https://example.com")

            assert crawler.metrics.total_requests == initial_total + 1


class TestSmartCrawlerGracefulDegradation:
    """Graceful degradation 테스트."""

    @pytest.mark.asyncio
    async def test_handles_playwright_import_error(self):
        """Playwright import 에러를 graceful하게 처리해야 합니다."""
        from app.services.search.crawler.protocol import CrawlResult
        from app.services.search.crawler.smart_crawler import SmartCrawler

        crawler = SmartCrawler(playwright_enabled=True)

        # Trafilatura 실패
        traf_result = CrawlResult(
            content="",
            title="",
            success=False,
            method="trafilatura",
            url="https://jobkorea.co.kr",
            error="JS-rendered",
        )

        with patch.object(crawler, "_trafilatura_crawler") as mock_traf:
            mock_traf.extract_content = AsyncMock(return_value=traf_result)
            mock_traf.can_handle = MagicMock(return_value=False)

            # Playwright가 ImportError를 발생시키는 경우
            with patch.object(crawler, "_playwright_crawler") as mock_pw:
                mock_pw.extract_content = AsyncMock(
                    side_effect=ImportError("Playwright not installed")
                )

                result = await crawler.extract_content("https://jobkorea.co.kr")

                # 에러가 발생해도 CrawlResult를 반환해야 함
                assert isinstance(result, CrawlResult)
                assert result.success is False
                assert (
                    "Playwright" in result.error
                    or "not installed" in result.error.lower()
                )


class TestGetSmartCrawler:
    """get_smart_crawler 팩토리 함수 테스트."""

    def test_get_smart_crawler_exists(self):
        """get_smart_crawler 함수가 존재해야 합니다."""
        from app.services.search.crawler.smart_crawler import get_smart_crawler

        assert callable(get_smart_crawler)

    def test_get_smart_crawler_returns_singleton(self):
        """get_smart_crawler가 싱글턴을 반환해야 합니다."""
        from app.services.search.crawler.smart_crawler import (
            get_smart_crawler,
            reset_smart_crawler,
        )

        reset_smart_crawler()

        crawler1 = get_smart_crawler()
        crawler2 = get_smart_crawler()

        assert crawler1 is crawler2
