"""ContentCrawlerService 단위 테스트.

TDD 방식으로 콘텐츠 크롤러 서비스의 동작을 검증합니다.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.content_crawler import (
    ContentCrawlerService,
    CrawlResult,
    get_content_crawler,
)


class TestCrawlResult:
    """CrawlResult 데이터 클래스 테스트."""

    def test_crawl_result_success(self):
        """성공적인 크롤링 결과를 생성할 수 있다."""
        result = CrawlResult(
            content="테스트 콘텐츠입니다.",
            title="테스트 제목",
            success=True,
            method="trafilatura",
            error=None,
        )

        assert result.success is True
        assert result.content == "테스트 콘텐츠입니다."
        assert result.title == "테스트 제목"
        assert result.method == "trafilatura"
        assert result.error is None

    def test_crawl_result_failure(self):
        """실패한 크롤링 결과를 생성할 수 있다."""
        result = CrawlResult(
            content="",
            title="",
            success=False,
            method="trafilatura",
            error="Connection timeout",
        )

        assert result.success is False
        assert result.content == ""
        assert result.error == "Connection timeout"


class TestContentCrawlerService:
    """ContentCrawlerService 테스트."""

    def test_init_default_settings(self):
        """기본 설정으로 초기화할 수 있다."""
        service = ContentCrawlerService()

        assert service.max_content_length == 2000
        assert service.timeout == 10.0
        assert service.max_concurrent == 5

    def test_init_custom_settings(self):
        """커스텀 설정으로 초기화할 수 있다."""
        service = ContentCrawlerService(
            max_content_length=3000,
            timeout=15.0,
            max_concurrent=10,
        )

        assert service.max_content_length == 3000
        assert service.timeout == 15.0
        assert service.max_concurrent == 10

    @pytest.mark.asyncio
    async def test_extract_content_success(self):
        """URL에서 콘텐츠를 성공적으로 추출할 수 있다."""
        service = ContentCrawlerService()

        # trafilatura 모킹
        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트 콘텐츠</body></html>"
            mock_extract.return_value = (
                "정보처리기사는 한국산업인력공단에서 시행하는 국가기술자격입니다."
            )
            mock_metadata.return_value = MagicMock(title="정보처리기사 시험 안내")

            result = await service.extract_content("https://example.com/test")

            assert result.success is True
            assert "정보처리기사" in result.content
            assert result.title == "정보처리기사 시험 안내"
            assert result.method == "trafilatura"

    @pytest.mark.asyncio
    async def test_extract_content_empty_response(self):
        """빈 응답 시 실패 결과를 반환한다."""
        service = ContentCrawlerService()

        with patch("app.services.search.content_crawler.fetch_url") as mock_fetch:
            mock_fetch.return_value = None

            result = await service.extract_content("https://example.com/empty")

            assert result.success is False
            assert result.content == ""
            assert "fetch" in result.error.lower() or "empty" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extract_content_no_text_extracted(self):
        """텍스트 추출 실패 시 적절히 처리한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
        ):

            mock_fetch.return_value = "<html><body></body></html>"
            mock_extract.return_value = None  # 추출 실패

            result = await service.extract_content("https://example.com/notext")

            assert result.success is False
            assert result.content == ""

    @pytest.mark.asyncio
    async def test_extract_content_truncates_long_content(self):
        """긴 콘텐츠는 max_content_length로 잘린다."""
        service = ContentCrawlerService(max_content_length=100)

        long_content = "가" * 500  # 500자

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>test</body></html>"
            mock_extract.return_value = long_content
            mock_metadata.return_value = MagicMock(title="Test")

            result = await service.extract_content("https://example.com/long")

            assert result.success is True
            assert len(result.content) <= 100

    @pytest.mark.asyncio
    async def test_extract_content_handles_exception(self):
        """예외 발생 시 실패 결과를 반환한다."""
        service = ContentCrawlerService()

        with patch("app.services.search.content_crawler.fetch_url") as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")

            result = await service.extract_content("https://example.com/error")

            assert result.success is False
            assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_extract_multiple_urls(self):
        """여러 URL을 병렬로 크롤링할 수 있다."""
        service = ContentCrawlerService(max_concurrent=3)

        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/page3",
        ]

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>test</body></html>"
            mock_extract.side_effect = ["콘텐츠 1", "콘텐츠 2", "콘텐츠 3"]
            mock_metadata.return_value = MagicMock(title="Test")

            results = await service.extract_multiple(urls)

            assert len(results) == 3
            assert all(isinstance(r, CrawlResult) for r in results)

    @pytest.mark.asyncio
    async def test_extract_multiple_handles_partial_failures(self):
        """일부 URL 실패 시에도 나머지 결과를 반환한다."""
        service = ContentCrawlerService()

        urls = [
            "https://example.com/success",
            "https://example.com/fail",
        ]

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            # 첫 번째는 성공, 두 번째는 실패
            mock_fetch.side_effect = ["<html>test</html>", None]
            mock_extract.return_value = "성공 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            results = await service.extract_multiple(urls)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False


class TestContentCrawlerSingleton:
    """싱글턴 패턴 테스트."""

    def test_get_content_crawler_returns_instance(self):
        """get_content_crawler가 인스턴스를 반환한다."""
        service = get_content_crawler()

        assert isinstance(service, ContentCrawlerService)

    def test_get_content_crawler_same_instance(self):
        """get_content_crawler가 동일한 인스턴스를 반환한다."""
        service1 = get_content_crawler()
        service2 = get_content_crawler()

        assert service1 is service2


class TestContentCrawlerExtractionOptions:
    """Trafilatura 추출 옵션 테스트."""

    @pytest.mark.asyncio
    async def test_extract_uses_precision_mode(self):
        """favor_precision=True 옵션을 사용한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트</body></html>"
            mock_extract.return_value = "테스트 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            await service.extract_content("https://example.com/test")

            # extract 함수가 favor_precision=True로 호출되었는지 확인
            mock_extract.assert_called_once()
            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs.get("favor_precision") is True

    @pytest.mark.asyncio
    async def test_extract_uses_formatting(self):
        """include_formatting=True 옵션을 사용한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트</body></html>"
            mock_extract.return_value = "테스트 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            await service.extract_content("https://example.com/test")

            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs.get("include_formatting") is True

    @pytest.mark.asyncio
    async def test_extract_uses_deduplication(self):
        """deduplicate=True 옵션을 사용한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트</body></html>"
            mock_extract.return_value = "테스트 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            await service.extract_content("https://example.com/test")

            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs.get("deduplicate") is True

    @pytest.mark.asyncio
    async def test_extract_includes_tables(self):
        """include_tables=True 옵션을 사용한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트</body></html>"
            mock_extract.return_value = "테스트 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            await service.extract_content("https://example.com/test")

            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs.get("include_tables") is True

    @pytest.mark.asyncio
    async def test_extract_targets_korean(self):
        """target_language='ko' 옵션을 사용한다."""
        service = ContentCrawlerService()

        with (
            patch("app.services.search.content_crawler.fetch_url") as mock_fetch,
            patch("app.services.search.content_crawler.extract") as mock_extract,
            patch(
                "app.services.search.content_crawler.extract_metadata"
            ) as mock_metadata,
        ):

            mock_fetch.return_value = "<html><body>테스트</body></html>"
            mock_extract.return_value = "테스트 콘텐츠"
            mock_metadata.return_value = MagicMock(title="Test")

            await service.extract_content("https://example.com/test")

            call_kwargs = mock_extract.call_args[1]
            assert call_kwargs.get("target_language") == "ko"


class TestContentCrawlerIntegration:
    """통합 테스트 (실제 네트워크 호출, 선택적 실행)."""

    @pytest.mark.skip(reason="실제 네트워크 호출 - 수동 실행 필요")
    @pytest.mark.asyncio
    async def test_real_crawl_qnet(self):
        """실제 큐넷 사이트 크롤링 테스트."""
        service = ContentCrawlerService()

        result = await service.extract_content(
            "https://www.q-net.or.kr/crf005.do?id=crf00505&gSite=Q&gId="
        )

        # 실제 크롤링 결과 확인
        print(f"Success: {result.success}")
        print(f"Title: {result.title}")
        print(f"Content length: {len(result.content)}")
        print(f"Content preview: {result.content[:200]}...")

        assert result.success is True
        assert len(result.content) > 100
