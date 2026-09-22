"""SearXNG + SmartCrawler 통합 테스트.

이 모듈은 SearXNG 검색 서비스에 SmartCrawler가 통합되었는지 테스트합니다.
"""

from unittest.mock import MagicMock, patch


class TestSearXNGSmartCrawlerIntegration:
    """SearXNG + SmartCrawler 통합 테스트."""

    def test_searxng_has_smart_crawler_option(self):
        """SearXNGSearchService에 use_smart_crawler 옵션이 있어야 합니다."""
        # 생성자에 use_smart_crawler 파라미터가 있는지 확인
        import inspect

        from app.services.search.searxng_search import SearXNGSearchService

        sig = inspect.signature(SearXNGSearchService.__init__)
        params = list(sig.parameters.keys())

        assert "use_smart_crawler" in params

    def test_searxng_uses_smart_crawler_by_default(self):
        """SearXNGSearchService가 기본적으로 SmartCrawler를 사용해야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=True)

            assert service.use_smart_crawler is True

    def test_searxng_can_disable_smart_crawler(self):
        """SmartCrawler를 비활성화할 수 있어야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=False,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=False)

            assert service.use_smart_crawler is False


class TestSearXNGCrawlerSelection:
    """크롤러 선택 테스트."""

    def test_get_crawler_returns_smart_crawler_when_enabled(self):
        """use_smart_crawler=True이면 SmartCrawler를 반환해야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=True)
            crawler = service._get_crawler()

            assert crawler.provider_name == "smart"

    def test_get_crawler_returns_content_crawler_when_disabled(self):
        """use_smart_crawler=False이면 ContentCrawlerService를 반환해야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=False,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=False)
            crawler = service._get_crawler()

            # ContentCrawlerService는 provider_name이 없으므로 타입으로 확인
            from app.services.search.content_crawler import ContentCrawlerService

            assert isinstance(crawler, ContentCrawlerService)


class TestCrawlingMetricsLogging:
    """크롤링 메트릭 로깅 테스트."""

    def test_searxng_logs_crawling_metrics(self):
        """SearXNGSearchService가 크롤링 메트릭을 로깅해야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=True)

            # get_crawling_metrics 메서드가 있어야 함
            assert hasattr(service, "get_crawling_metrics")
            assert callable(service.get_crawling_metrics)

    def test_get_crawling_metrics_returns_dict(self):
        """get_crawling_metrics가 딕셔너리를 반환해야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService(use_smart_crawler=True)
            metrics = service.get_crawling_metrics()

            assert isinstance(metrics, dict)
            assert "total_requests" in metrics


class TestExamScheduleQueries:
    """시험 일정 쿼리 테스트."""

    def test_comprehensive_queries_includes_exam_schedule(self):
        """_build_comprehensive_queries에 exam_schedule이 포함되어야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService()
            queries = service._build_comprehensive_queries("정보처리기사")

            assert "exam_schedule" in queries
            assert "시험 일정" in queries["exam_schedule"]["query"]
            assert "접수" in queries["exam_schedule"]["query"]

    def test_exam_schedule_query_has_required_keywords(self):
        """exam_schedule 쿼리에 필수 키워드가 포함되어야 합니다."""
        with patch("app.services.search.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                SEARXNG_BASE_URL="http://localhost:8888",
                SEARXNG_TIMEOUT=30.0,
                PLAYWRIGHT_ENABLED=True,
                SEARCH_OFFICIAL_SOURCE_REQUIRED=True,
            )

            from app.services.search.searxng_search import SearXNGSearchService

            service = SearXNGSearchService()
            queries = service._build_comprehensive_queries("정보처리기사")

            exam_schedule = queries["exam_schedule"]
            required_keywords = ["시험 일정", "접수 기간", "시험일"]

            for keyword in required_keywords:
                assert (
                    keyword in exam_schedule["keywords"]
                ), f"Missing keyword: {keyword}"
