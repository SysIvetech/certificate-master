"""CrawlerProtocol 및 크롤러 팩토리 테스트.

이 모듈은 크롤러 프로토콜 인터페이스와 팩토리 패턴을 테스트합니다.
"""


class TestCrawlerProtocol:
    """CrawlerProtocol 인터페이스 테스트."""

    def test_protocol_can_be_imported(self):
        """CrawlerProtocol을 임포트할 수 있어야 합니다."""
        from app.services.search.crawler.protocol import CrawlerProtocol

        assert CrawlerProtocol is not None
        assert hasattr(CrawlerProtocol, "provider_name")
        assert hasattr(CrawlerProtocol, "extract_content")
        assert hasattr(CrawlerProtocol, "can_handle")

    def test_protocol_is_runtime_checkable(self):
        """CrawlerProtocol은 runtime_checkable이어야 합니다."""
        from app.services.search.crawler.protocol import CrawlerProtocol

        # runtime_checkable 프로토콜은 isinstance 체크 가능
        assert hasattr(CrawlerProtocol, "__protocol_attrs__") or callable(
            getattr(CrawlerProtocol, "_is_protocol", None)
        )

    def test_crawl_result_dataclass_exists(self):
        """CrawlResult 데이터클래스가 존재해야 합니다."""
        from app.services.search.crawler.protocol import CrawlResult

        # 필수 필드 확인
        result = CrawlResult(
            content="테스트 콘텐츠",
            title="테스트 제목",
            success=True,
            method="test",
            url="https://example.com",
        )

        assert result.content == "테스트 콘텐츠"
        assert result.title == "테스트 제목"
        assert result.success is True
        assert result.method == "test"
        assert result.url == "https://example.com"
        assert result.error is None  # 선택적 필드


class TestCrawlerFactory:
    """크롤러 팩토리 테스트."""

    def test_factory_can_be_imported(self):
        """get_crawler 팩토리 함수를 임포트할 수 있어야 합니다."""
        from app.services.search.crawler.factory import get_crawler

        assert callable(get_crawler)

    def test_factory_returns_crawler_protocol(self):
        """팩토리가 CrawlerProtocol을 구현한 객체를 반환해야 합니다."""
        from app.services.search.crawler.factory import get_crawler

        crawler = get_crawler()

        # 프로토콜 속성 확인
        assert hasattr(crawler, "provider_name")
        assert hasattr(crawler, "extract_content")
        assert hasattr(crawler, "can_handle")

    def test_get_crawler_for_url_returns_appropriate_crawler(self):
        """URL에 따라 적절한 크롤러를 반환해야 합니다."""
        from app.services.search.crawler.factory import get_crawler_for_url

        # 일반 사이트는 trafilatura 크롤러
        crawler = get_crawler_for_url("https://example.com")
        assert crawler.provider_name == "trafilatura"

        # JS 렌더링 사이트는 playwright 크롤러
        crawler = get_crawler_for_url("https://m.jobkorea.co.kr/job/123")
        assert crawler.provider_name == "playwright"

    def test_get_crawler_for_url_with_playwright_disabled(self):
        """Playwright가 비활성화되면 항상 trafilatura를 반환해야 합니다."""
        from app.services.search.crawler.factory import get_crawler_for_url

        # Playwright 비활성화 상태에서 JS 사이트도 trafilatura 사용
        crawler = get_crawler_for_url(
            "https://m.jobkorea.co.kr/job/123",
            playwright_enabled=False,
        )
        assert crawler.provider_name == "trafilatura"


class TestTrafilaturaCrawler:
    """Trafilatura 크롤러 테스트."""

    def test_trafilatura_crawler_implements_protocol(self):
        """TrafilaturaCrawler가 CrawlerProtocol을 구현해야 합니다."""
        from app.services.search.crawler.trafilatura_crawler import TrafilaturaCrawler

        crawler = TrafilaturaCrawler()

        assert crawler.provider_name == "trafilatura"
        assert hasattr(crawler, "extract_content")
        assert hasattr(crawler, "can_handle")

    def test_trafilatura_can_handle_regular_urls(self):
        """Trafilatura는 일반 URL을 처리할 수 있어야 합니다."""
        from app.services.search.crawler.trafilatura_crawler import TrafilaturaCrawler

        crawler = TrafilaturaCrawler()

        # 일반 웹사이트
        assert crawler.can_handle("https://example.com") is True
        assert crawler.can_handle("https://blog.naver.com/abc") is True

        # PDF 등 파일은 처리 불가
        assert crawler.can_handle("https://example.com/file.pdf") is False

    def test_trafilatura_cannot_handle_js_sites(self):
        """Trafilatura는 JS 렌더링 사이트를 처리할 수 없어야 합니다."""
        from app.services.search.crawler.trafilatura_crawler import TrafilaturaCrawler

        crawler = TrafilaturaCrawler()

        # JS 렌더링 사이트
        assert crawler.can_handle("https://m.jobkorea.co.kr/job/123") is False
        assert crawler.can_handle("https://m.saramin.co.kr/job/456") is False


class TestPlaywrightCrawler:
    """Playwright 크롤러 테스트 (기본 구조만)."""

    def test_playwright_crawler_can_be_imported(self):
        """PlaywrightCrawler를 임포트할 수 있어야 합니다."""
        from app.services.search.crawler.playwright_crawler import PlaywrightCrawler

        assert PlaywrightCrawler is not None

    def test_playwright_crawler_implements_protocol(self):
        """PlaywrightCrawler가 CrawlerProtocol 속성을 가져야 합니다."""
        from app.services.search.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler()

        assert crawler.provider_name == "playwright"
        assert hasattr(crawler, "extract_content")
        assert hasattr(crawler, "can_handle")

    def test_playwright_can_handle_js_sites(self):
        """Playwright는 JS 렌더링 사이트를 처리할 수 있어야 합니다."""
        from app.services.search.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler()

        # JS 렌더링 사이트
        assert crawler.can_handle("https://m.jobkorea.co.kr/job/123") is True
        assert crawler.can_handle("https://m.saramin.co.kr/job/456") is True
        assert crawler.can_handle("https://wanted.co.kr/wd/123") is True

    def test_playwright_can_handle_regular_sites_too(self):
        """Playwright는 일반 사이트도 처리할 수 있어야 합니다."""
        from app.services.search.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler()

        # 일반 웹사이트도 처리 가능 (fallback 용도)
        assert crawler.can_handle("https://example.com") is True


class TestPlaywrightDomains:
    """Playwright가 필요한 도메인 목록 테스트."""

    def test_playwright_required_domains_exist(self):
        """PLAYWRIGHT_REQUIRED_DOMAINS 상수가 존재해야 합니다."""
        from app.services.search.crawler.playwright_crawler import (
            PLAYWRIGHT_REQUIRED_DOMAINS,
        )

        assert isinstance(PLAYWRIGHT_REQUIRED_DOMAINS, set)
        assert len(PLAYWRIGHT_REQUIRED_DOMAINS) > 0

    def test_known_js_sites_in_domains(self):
        """알려진 JS 사이트가 도메인 목록에 포함되어야 합니다."""
        from app.services.search.crawler.playwright_crawler import (
            PLAYWRIGHT_REQUIRED_DOMAINS,
        )

        # 계획에 명시된 사이트들
        expected_domains = {
            "jobkorea.co.kr",
            "saramin.co.kr",
            "wanted.co.kr",
            "incruit.com",
        }

        for domain in expected_domains:
            assert domain in PLAYWRIGHT_REQUIRED_DOMAINS, f"{domain} should be included"
