"""SearchServiceProtocol 및 팩토리 테스트."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSearchServiceProtocol:
    """SearchServiceProtocol 테스트."""

    def test_searxng_service_implements_protocol(self):
        """SearXNGSearchService가 프로토콜을 구현하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        assert isinstance(service, SearchServiceProtocol)

    def test_protocol_has_provider_name_property(self):
        """프로토콜이 provider_name 속성을 요구하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol

        assert hasattr(SearchServiceProtocol, "provider_name")

    def test_protocol_has_search_method(self):
        """프로토콜이 search 메서드를 요구하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol

        assert hasattr(SearchServiceProtocol, "search")

    def test_protocol_has_search_certificate_comprehensive_method(self):
        """프로토콜이 search_certificate_comprehensive 메서드를 요구하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol

        assert hasattr(SearchServiceProtocol, "search_certificate_comprehensive")

    def test_protocol_has_search_study_plan_context_method(self):
        """프로토콜이 search_study_plan_context 메서드를 요구하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol

        assert hasattr(SearchServiceProtocol, "search_study_plan_context")

    def test_protocol_has_format_search_results_for_llm_method(self):
        """프로토콜이 format_search_results_for_llm 메서드를 요구하는지 테스트."""
        from app.services.search_protocol import SearchServiceProtocol

        assert hasattr(SearchServiceProtocol, "format_search_results_for_llm")


class TestSearchFactory:
    """검색 팩토리 테스트."""

    def test_get_search_service_returns_searxng(self):
        """기본 검색 서비스가 SearXNG인지 테스트."""
        from app.services.search_factory import get_search_service
        from app.services.searxng_search import SearXNGSearchService

        service = get_search_service()
        assert isinstance(service, SearXNGSearchService)


class TestSearXNGSearchService:
    """SearXNGSearchService 테스트."""

    def test_init_default_config(self):
        """기본 설정으로 초기화 테스트."""
        with patch("app.services.searxng_search.get_settings") as mock_settings:
            mock_settings.return_value.SEARXNG_BASE_URL = "http://localhost:8888"
            mock_settings.return_value.SEARXNG_TIMEOUT = 30.0

            from app.services.searxng_search import SearXNGSearchService

            service = SearXNGSearchService()
            assert service.base_url == "http://localhost:8888"
            assert service.timeout == 30.0
            assert service.provider_name == "searxng"

    def test_init_custom_config(self):
        """커스텀 설정으로 초기화 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(
            base_url="http://custom:9999",
            timeout=60.0,
        )
        assert service.base_url == "http://custom:9999"
        assert service.timeout == 60.0

    def test_provider_name(self):
        """provider_name 속성 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        assert service.provider_name == "searxng"

    def test_calculate_url_quality_prioritizes_official_sources(self):
        """URL 품질이 공식 출처를 우선하는지 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        assert service._calculate_url_quality("https://www.q-net.or.kr") == 100
        assert service._calculate_url_quality("https://hrdkorea.or.kr") == 100
        assert service._calculate_url_quality("https://www.eduwill.net") == 90
        assert service._calculate_url_quality("https://www.hackers.com") == 90

    def test_calculate_recency_score_parses_age(self):
        """최신성 점수가 age 문자열을 파싱하는지 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        assert service._calculate_recency_score("2 months ago") == 60
        assert service._calculate_recency_score("1 year ago") == 35
        assert service._calculate_recency_score("today") == 95

    def test_parse_publish_date_iso_format(self):
        """ISO 형식 날짜 파싱 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        # 빈 문자열
        assert service._parse_publish_date("") == ""

        # 잘못된 형식은 원본 반환
        result = service._parse_publish_date("invalid-date")
        assert result == "invalid-date"

    def test_extract_results_keyword_hints_boost_relevance(self):
        """키워드 힌트가 관련성 점수를 높이는지 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        api_response = {
            "web": {
                "results": [
                    {
                        "title": "기본 정보",
                        "url": "https://example.com/info",
                        "description": "일반 설명입니다.",
                        "age": "",
                    },
                    {
                        "title": "합격률 통계",
                        "url": "https://example.com/stats",
                        "description": "합격률 관련 데이터 포함",
                        "age": "",
                    },
                ]
            }
        }

        results = service._extract_results(
            api_response,
            keyword_hints=["합격률", "통계"],
        )

        assert results[0]["title"] == "합격률 통계"
        assert results[0]["keyword_score"] > results[1]["keyword_score"]

    @pytest.mark.anyio
    async def test_search_returns_brave_compatible_format(self):
        """검색 결과가 Brave API 호환 형식인지 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(base_url="http://localhost:8888")

        mock_response_data = {
            "results": [
                {
                    "title": "테스트 결과",
                    "url": "https://example.com",
                    "content": "테스트 설명",
                    "publishedDate": "2025-01-01T00:00:00Z",
                }
            ]
        }

        with patch("app.services.searxng_search.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance

            mock_response = MagicMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status = MagicMock()
            mock_instance.get.return_value = mock_response

            result = await service.search("테스트 쿼리")

        # Brave API 호환 형식 확인
        assert "web" in result
        assert "results" in result["web"]
        assert len(result["web"]["results"]) == 1
        assert result["web"]["results"][0]["title"] == "테스트 결과"
        assert result["web"]["results"][0]["description"] == "테스트 설명"

    @pytest.mark.anyio
    async def test_search_study_plan_context_runs_all_queries(self):
        """학습 계획 검색이 모든 카테고리를 조회하는지 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        with (
            patch.object(
                service,
                "search",
                new_callable=AsyncMock,
                return_value={"web": {"results": []}},
            ) as mock_search,
            patch.object(
                service,
                "_extract_results",
                return_value=[],
            ) as mock_extract,
            patch(
                "app.services.searxng_search.asyncio.sleep",
                new_callable=AsyncMock,
            ),
        ):
            results = await service.search_study_plan_context(
                "정보처리기사",
                delay_seconds=0,
            )

        assert "exam_schedule" in results
        assert "study_plan_examples" in results
        assert "time_allocation" in results
        assert mock_search.call_count == len(results)

        for call in mock_extract.call_args_list:
            assert "keyword_hints" in call.kwargs

    def test_format_search_results_for_llm(self):
        """LLM용 포맷 생성 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        search_results = {
            "general": [
                {
                    "title": "테스트 제목",
                    "url": "https://q-net.or.kr/test",
                    "description": "테스트 설명",
                    "age": "1 day ago",
                    "url_quality": 100,
                    "recency_score": 95,
                }
            ],
            "statistics": [],
        }

        result = service.format_search_results_for_llm(search_results)

        assert "자격증 정보 검색 결과" in result
        assert "테스트 제목" in result
        assert "공식 사이트" in result
        assert "검색 결과 없음" in result

    def test_build_comprehensive_queries(self):
        """종합 쿼리 생성 테스트."""
        from app.services.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        queries = service._build_comprehensive_queries("정보처리기사")

        assert "general" in queries
        assert "statistics" in queries
        assert "career" in queries
        assert "reviews" in queries
        assert "study_methods" in queries
        assert "books" in queries
        assert "lectures" in queries
        assert "official" in queries

        for category, payload in queries.items():
            assert "query" in payload
            assert "keywords" in payload
            assert "정보처리기사" in payload["query"]
