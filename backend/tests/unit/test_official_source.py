"""공식 출처 확보 로직 테스트.

이 모듈은 검색 결과에서 공식 출처(Q-Net 등)가 필수로 포함되는지 테스트합니다.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOfficialSourceDetection:
    """공식 출처 감지 테스트."""

    def test_has_official_source_function_exists(self):
        """has_official_source 함수가 존재해야 합니다."""
        from app.services.search.searxng_search import has_official_source

        assert callable(has_official_source)

    def test_detects_qnet_in_results(self):
        """Q-Net URL이 포함된 결과를 감지해야 합니다."""
        from app.services.search.searxng_search import has_official_source

        results = [
            {"url": "https://blog.naver.com/abc"},
            {"url": "https://www.q-net.or.kr/crf005.do"},
        ]

        assert has_official_source(results) is True

    def test_detects_hrdkorea_in_results(self):
        """HRD Korea URL이 포함된 결과를 감지해야 합니다."""
        from app.services.search.searxng_search import has_official_source

        results = [
            {"url": "https://blog.naver.com/abc"},
            {"url": "https://www.hrdkorea.or.kr/main/main.do"},
        ]

        assert has_official_source(results) is True

    def test_returns_false_when_no_official(self):
        """공식 출처가 없으면 False를 반환해야 합니다."""
        from app.services.search.searxng_search import has_official_source

        results = [
            {"url": "https://blog.naver.com/abc"},
            {"url": "https://tistory.com/123"},
            {"url": "https://saramin.co.kr/job/456"},
        ]

        assert has_official_source(results) is False

    def test_returns_false_for_empty_results(self):
        """빈 결과에 대해 False를 반환해야 합니다."""
        from app.services.search.searxng_search import has_official_source

        assert has_official_source([]) is False


class TestEnsureOfficialSource:
    """공식 출처 필수 확보 테스트."""

    @pytest.mark.asyncio
    async def test_ensure_official_source_method_exists(self):
        """_ensure_official_source 메서드가 존재해야 합니다."""
        from app.services.search.searxng_search import SearXNGSearchService

        # Mock 설정
        with patch.object(SearXNGSearchService, "__init__", lambda x: None):
            service = SearXNGSearchService()
            service.crawl_enabled = False

            assert hasattr(service, "_ensure_official_source")
            assert callable(service._ensure_official_source)

    @pytest.mark.asyncio
    async def test_ensure_official_does_not_modify_when_present(self):
        """공식 출처가 있으면 결과를 수정하지 않아야 합니다."""
        from app.services.search.searxng_search import SearXNGSearchService

        # Mock search 메서드
        with patch.object(SearXNGSearchService, "__init__", lambda x: None):
            service = SearXNGSearchService()
            service.crawl_enabled = False
            service.search = AsyncMock()

            results = {
                "official": [
                    {"url": "https://www.q-net.or.kr/crf005.do", "title": "큐넷"},
                ],
                "general": [
                    {"url": "https://blog.naver.com/abc", "title": "블로그"},
                ],
            }

            # 공식 출처가 이미 있으므로 search가 호출되지 않아야 함
            updated = await service._ensure_official_source("정보처리기사", results)

            service.search.assert_not_called()
            assert "official" in updated
            assert len(updated["official"]) >= 1

    @pytest.mark.asyncio
    async def test_ensure_official_adds_fallback_when_missing(self):
        """공식 출처가 없으면 fallback 검색을 수행해야 합니다."""
        from app.services.search.searxng_search import SearXNGSearchService

        with patch.object(SearXNGSearchService, "__init__", lambda x: None):
            service = SearXNGSearchService()
            service.crawl_enabled = False

            # Mock search - fallback 검색 결과
            fallback_result = {
                "web": {
                    "results": [
                        {
                            "title": "정보처리기사 | Q-Net",
                            "url": "https://www.q-net.or.kr/crf005.do",
                            "content": "정보처리기사 시험 정보",
                        }
                    ]
                }
            }
            service.search = AsyncMock(return_value=fallback_result)
            service._extract_results = MagicMock(
                return_value=[
                    {
                        "title": "정보처리기사 | Q-Net",
                        "url": "https://www.q-net.or.kr/crf005.do",
                        "description": "정보처리기사 시험 정보",
                    }
                ]
            )

            results = {
                "official": [],  # 공식 출처 없음
                "general": [
                    {"url": "https://blog.naver.com/abc", "title": "블로그"},
                ],
            }

            await service._ensure_official_source("정보처리기사", results)

            # fallback 검색이 호출되었는지 확인
            service.search.assert_called_once()
            call_args = service.search.call_args
            assert "site:q-net.or.kr" in call_args[0][0]


class TestSearchWithOfficialSource:
    """공식 출처 포함 검색 테스트."""

    @pytest.mark.asyncio
    async def test_comprehensive_search_includes_official(self):
        """종합 검색에 공식 출처가 포함되어야 합니다."""
        from app.services.search.searxng_search import SearXNGSearchService

        with patch.object(SearXNGSearchService, "__init__", lambda x: None):
            service = SearXNGSearchService()
            service.crawl_enabled = False

            # _run_categorized_queries를 mock
            mock_results = {
                "general": [{"url": "https://example.com", "title": "일반"}],
                "official": [{"url": "https://q-net.or.kr", "title": "공식"}],
            }

            service._run_categorized_queries = AsyncMock(return_value=mock_results)
            service._ensure_official_source = AsyncMock(return_value=mock_results)
            service._build_comprehensive_queries = MagicMock(return_value={})

            await service.search_certificate_comprehensive("정보처리기사")

            # _ensure_official_source가 호출되었는지 확인
            service._ensure_official_source.assert_called_once()


class TestOfficialSourceConfig:
    """공식 출처 설정 테스트."""

    def test_config_official_source_required_exists(self):
        """SEARCH_OFFICIAL_SOURCE_REQUIRED 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "SEARCH_OFFICIAL_SOURCE_REQUIRED" in Settings.__annotations__

    def test_official_source_required_default_is_true(self):
        """SEARCH_OFFICIAL_SOURCE_REQUIRED 기본값이 True여야 합니다."""
        from app.core.config import Settings

        fields = Settings.model_fields
        assert fields["SEARCH_OFFICIAL_SOURCE_REQUIRED"].default is True
