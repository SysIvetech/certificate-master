"""Unit tests for SearXNGSearchService.

TDD: 검색 서비스 테스트 (SearXNG 전용).
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestSearXNGSearchService:
    """Tests for SearXNGSearchService."""

    def test_init_with_base_url(self):
        """Test service initialization with base URL."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(base_url="http://localhost:8888")
        assert service.base_url == "http://localhost:8888"
        assert service.provider_name == "searxng"

    def test_calculate_url_quality_prioritizes_official_sources(self):
        """URL quality should prioritize official domains."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        assert service._calculate_url_quality("https://www.q-net.or.kr") == 100
        assert service._calculate_url_quality("https://hrdkorea.or.kr") == 100
        assert service._calculate_url_quality("https://www.eduwill.net") == 90
        assert service._calculate_url_quality("https://www.hackers.com") == 90

    def test_calculate_recency_score_parses_age(self):
        """Recency score should parse age strings."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        assert service._calculate_recency_score("2 months ago") == 60
        assert service._calculate_recency_score("1 year ago") == 35
        assert service._calculate_recency_score("today") == 95

    def test_extract_results_keyword_hints_boost_relevance(self):
        """Keyword hints should boost ranking when matched."""
        from app.services.search.searxng_search import SearXNGSearchService

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

    @pytest.mark.asyncio
    async def test_search_study_plan_context_runs_all_queries(self):
        """Study plan search should call all categories with hints."""
        from app.services.search.searxng_search import SearXNGSearchService

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
            ),
            patch(
                "app.services.search.searxng_search.asyncio.sleep",
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

    def test_comprehensive_queries_include_job_seeker_categories(self):
        """종합 검색에 취업준비생 관점 카테고리가 포함되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        queries = service._build_comprehensive_queries("정보처리기사")

        # 취업준비생 필수 카테고리 확인
        job_seeker_categories = [
            "job_postings",  # 채용공고 우대/필수
            "public_sector",  # 공무원/공기업 가산점
            "cost_breakdown",  # 총 비용 (교재+인강+응시료)
            "non_major_reviews",  # 비전공자/직장인 합격기
            "free_resources",  # 기출문제/무료 자료
            "comparison",  # 유사 자격증 비교
        ]

        for category in job_seeker_categories:
            assert category in queries, f"Missing category: {category}"
            assert "query" in queries[category]
            assert "keywords" in queries[category]

    def test_job_postings_query_includes_employment_keywords(self):
        """채용공고 카테고리에 취업 관련 키워드가 포함되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        queries = service._build_comprehensive_queries("정보처리기사")

        job_query = queries["job_postings"]
        assert "채용" in job_query["query"] or "우대" in job_query["query"]
        assert any(
            kw in job_query["keywords"] for kw in ["채용", "우대", "필수", "가산점"]
        )

    def test_public_sector_query_includes_government_keywords(self):
        """공무원/공기업 카테고리에 관련 키워드가 포함되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        queries = service._build_comprehensive_queries("정보처리기사")

        public_query = queries["public_sector"]
        assert any(kw in public_query["query"] for kw in ["공무원", "공기업", "가산점"])
        assert any(
            kw in public_query["keywords"] for kw in ["공무원", "공기업", "가산점"]
        )

    def test_cost_breakdown_query_includes_expense_keywords(self):
        """비용 카테고리에 비용 관련 키워드가 포함되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()
        queries = service._build_comprehensive_queries("정보처리기사")

        cost_query = queries["cost_breakdown"]
        assert any(kw in cost_query["query"] for kw in ["비용", "가격", "응시료"])
        assert any(
            kw in cost_query["keywords"] for kw in ["비용", "가격", "교재", "인강"]
        )

    def test_url_quality_prioritizes_job_sites(self):
        """URL 품질 점수에 채용 사이트가 우선순위로 포함되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        # 채용 사이트는 높은 점수 (90점 이상)
        assert service._calculate_url_quality("https://www.saramin.co.kr") >= 90
        assert service._calculate_url_quality("https://www.jobkorea.co.kr") >= 90
        assert service._calculate_url_quality("https://www.wanted.co.kr") >= 90


class TestUrlPrioritization:
    """URL 우선순위 정렬 테스트 (PDF/파일 후순위)."""

    def test_prioritize_urls_puts_pdf_last(self):
        """PDF URL은 후순위로 정렬되어야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        results = [
            {"url": "https://example.com/doc.pdf", "title": "PDF 문서"},
            {"url": "https://example.com/page.html", "title": "웹페이지"},
            {"url": "https://example.com/data.xlsx", "title": "엑셀 파일"},
            {"url": "https://blog.example.com/post", "title": "블로그 포스트"},
        ]

        prioritized = service._prioritize_urls(results)

        # 웹페이지가 먼저, 파일은 나중에
        assert prioritized[0]["title"] == "웹페이지"
        assert prioritized[1]["title"] == "블로그 포스트"
        # PDF, Excel은 마지막
        assert prioritized[2]["url"].endswith((".pdf", ".xlsx"))
        assert prioritized[3]["url"].endswith((".pdf", ".xlsx"))

    def test_prioritize_urls_handles_various_file_extensions(self):
        """다양한 파일 확장자를 후순위로 처리해야 함."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        file_extensions = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".hwp"]
        results = [
            {"url": f"https://example.com/file{ext}", "title": f"파일 {ext}"}
            for ext in file_extensions
        ] + [
            {"url": "https://example.com/normal-page", "title": "일반 페이지"},
        ]

        prioritized = service._prioritize_urls(results)

        # 일반 페이지가 첫 번째
        assert prioritized[0]["title"] == "일반 페이지"

    def test_prioritize_urls_preserves_order_within_same_priority(self):
        """같은 우선순위 내에서는 원래 순서 유지."""
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService()

        results = [
            {"url": "https://a.com/page1", "title": "A"},
            {"url": "https://b.com/page2", "title": "B"},
            {"url": "https://c.com/page3", "title": "C"},
        ]

        prioritized = service._prioritize_urls(results)

        # 모두 웹페이지이므로 원래 순서 유지
        assert [r["title"] for r in prioritized] == ["A", "B", "C"]


class TestSequentialCrawlWithFallback:
    """순차 크롤링 + Fallback 테스트."""

    @pytest.mark.asyncio
    async def test_crawl_stops_after_target_success_count(self):
        """목표 성공 수(3개)에 도달하면 크롤링 중단."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.search.content_crawler import CrawlResult
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(crawl_enabled=True, crawl_target_success=3)

        # Mock crawler - 모든 크롤링 성공
        mock_crawler = MagicMock()
        mock_crawler.extract_content = AsyncMock(
            return_value=CrawlResult(
                content="크롤링된 콘텐츠",
                title="제목",
                success=True,
                method="trafilatura",
                error=None,
            )
        )
        service._crawler = mock_crawler

        # 10개 검색 결과
        search_response = {
            "web": {
                "results": [
                    {
                        "title": f"결과 {i}",
                        "url": f"https://example{i}.com/page",
                        "description": f"설명 {i}",
                    }
                    for i in range(10)
                ]
            }
        }

        results = await service._extract_results_with_crawl(search_response)

        # 3개만 크롤링되어야 함
        assert mock_crawler.extract_content.call_count == 3
        # 크롤링된 3개는 full_content 있음
        crawled_count = sum(1 for r in results if r.get("full_content"))
        assert crawled_count == 3

    @pytest.mark.asyncio
    async def test_crawl_uses_snippet_fallback_on_failure(self):
        """크롤링 실패 시 검색 snippet을 fallback으로 사용."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.search.content_crawler import CrawlResult
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(crawl_enabled=True, crawl_target_success=3)

        # Mock crawler - 모든 크롤링 실패
        mock_crawler = MagicMock()
        mock_crawler.extract_content = AsyncMock(
            return_value=CrawlResult(
                content="",
                title="",
                success=False,
                method="trafilatura",
                error="Failed to crawl",
            )
        )
        service._crawler = mock_crawler

        # 검색 결과 (description에 snippet 있음)
        search_response = {
            "web": {
                "results": [
                    {
                        "title": f"결과 {i}",
                        "url": f"https://example{i}.com/page",
                        "description": f"검색 snippet {i}",
                    }
                    for i in range(5)
                ]
            }
        }

        results = await service._extract_results_with_crawl(search_response)

        # fallback으로 snippet 사용
        assert results[0]["full_content"] == "검색 snippet 0"
        assert results[0]["crawl_method"] == "snippet_fallback"

    @pytest.mark.asyncio
    async def test_crawl_skips_pdf_tries_next(self):
        """PDF는 후순위로 정렬되어 웹페이지 먼저 크롤링."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.search.content_crawler import CrawlResult
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(crawl_enabled=True, crawl_target_success=2)

        # Mock crawler
        mock_crawler = MagicMock()
        mock_crawler.extract_content = AsyncMock(
            return_value=CrawlResult(
                content="웹 콘텐츠",
                title="제목",
                success=True,
                method="trafilatura",
                error=None,
            )
        )
        service._crawler = mock_crawler

        # PDF가 먼저 있는 검색 결과
        search_response = {
            "web": {
                "results": [
                    {
                        "title": "PDF 문서",
                        "url": "https://example.com/doc.pdf",
                        "description": "PDF",
                    },
                    {
                        "title": "웹페이지 1",
                        "url": "https://example.com/page1",
                        "description": "웹1",
                    },
                    {
                        "title": "웹페이지 2",
                        "url": "https://example.com/page2",
                        "description": "웹2",
                    },
                ]
            }
        }

        await service._extract_results_with_crawl(search_response)

        # 웹페이지만 크롤링 시도 (PDF는 후순위)
        crawled_urls = [
            call.args[0] for call in mock_crawler.extract_content.call_args_list
        ]
        assert "https://example.com/doc.pdf" not in crawled_urls
        assert "https://example.com/page1" in crawled_urls
        assert "https://example.com/page2" in crawled_urls

    @pytest.mark.asyncio
    async def test_crawl_continues_on_failure_without_snippet_until_target(self):
        """snippet 없이 실패하면 목표 성공 수까지 계속 시도."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.search.content_crawler import CrawlResult
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(crawl_enabled=True, crawl_target_success=2)

        # Mock crawler - 1,2번 실패, 3,4번 성공
        call_count = 0

        async def mock_extract(url):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return CrawlResult(
                    content="",
                    title="",
                    success=False,
                    method="trafilatura",
                    error="Failed",
                )
            return CrawlResult(
                content=f"콘텐츠 {call_count}",
                title="제목",
                success=True,
                method="trafilatura",
                error=None,
            )

        mock_crawler = MagicMock()
        mock_crawler.extract_content = AsyncMock(side_effect=mock_extract)
        service._crawler = mock_crawler

        # description(snippet)이 없는 검색 결과
        search_response = {
            "web": {
                "results": [
                    {
                        "title": f"결과 {i}",
                        "url": f"https://example{i}.com/page",
                        "description": "",
                    }
                    for i in range(6)
                ]
            }
        }

        await service._extract_results_with_crawl(search_response)

        # 1,2번 실패 (snippet 없음) + 3,4번 성공 = 4번 호출
        # 목표 2개 달성 후 중단
        assert mock_crawler.extract_content.call_count == 4

    @pytest.mark.asyncio
    async def test_snippet_fallback_counts_as_success(self):
        """snippet fallback도 성공으로 카운트됨."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.search.content_crawler import CrawlResult
        from app.services.search.searxng_search import SearXNGSearchService

        service = SearXNGSearchService(crawl_enabled=True, crawl_target_success=2)

        # Mock crawler - 모두 실패
        mock_crawler = MagicMock()
        mock_crawler.extract_content = AsyncMock(
            return_value=CrawlResult(
                content="",
                title="",
                success=False,
                method="trafilatura",
                error="Failed",
            )
        )
        service._crawler = mock_crawler

        # description(snippet)이 있는 검색 결과
        search_response = {
            "web": {
                "results": [
                    {
                        "title": f"결과 {i}",
                        "url": f"https://example{i}.com/page",
                        "description": f"snippet {i}",
                    }
                    for i in range(6)
                ]
            }
        }

        results = await service._extract_results_with_crawl(search_response)

        # snippet fallback도 성공으로 카운트되므로 2번만 호출
        assert mock_crawler.extract_content.call_count == 2
        # snippet이 full_content로 사용됨
        assert results[0]["full_content"] == "snippet 0"
        assert results[0]["crawl_method"] == "snippet_fallback"
