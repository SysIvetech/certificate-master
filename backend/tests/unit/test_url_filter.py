"""URL 필터링 테스트.

파일 다운로드 URL을 크롤링하지 않도록 필터링하는 기능을 테스트합니다.

테스트 대상:
1. 파일 다운로드 URL 필터링 (is_crawlable_url)
2. JS 렌더링 사이트 감지 (is_js_rendered_domain)
3. Snippet 품질 검증 (is_valid_snippet)
4. 도메인별 실패 캐싱 (DomainFailureCache)
"""

import pytest

from app.services.search.content_crawler import ContentCrawlerService, is_crawlable_url


class TestIsCrawlableUrl:
    """is_crawlable_url 함수 테스트."""

    def test_normal_html_url_is_crawlable(self):
        """일반 HTML 페이지 URL은 크롤링 가능."""
        assert (
            is_crawlable_url(
                "https://www.q-net.or.kr/crf005.do?id=crf00503&gSite=Q&gId="
            )
            is True
        )
        assert is_crawlable_url("https://blog.naver.com/example/12345") is True
        assert is_crawlable_url("https://www.saramin.co.kr/job/123456") is True

    def test_download_url_patterns_not_crawlable(self):
        """파일 다운로드 URL 패턴은 크롤링 불가."""
        # downloadFile.do 패턴
        assert (
            is_crawlable_url(
                "https://www.moel.go.kr/common/downloadFile.do?file_seq=20200"
            )
            is False
        )

        # flDownload.do 패턴
        assert (
            is_crawlable_url("https://www.law.go.kr/flDownload.do?flSeq=150751385")
            is False
        )

        # BOARD_ATTACH 패턴
        assert (
            is_crawlable_url(
                "https://www.msu.ac.kr/download/BOARD_ATTACH?storageNo=18620"
            )
            is False
        )

        # /download/ 경로 패턴
        assert is_crawlable_url("https://example.com/download/file123") is False

    def test_file_extension_urls_not_crawlable(self):
        """파일 확장자 URL은 크롤링 불가."""
        assert is_crawlable_url("https://example.com/document.pdf") is False
        assert is_crawlable_url("https://example.com/file.hwp") is False
        assert is_crawlable_url("https://example.com/data.xlsx") is False
        assert is_crawlable_url("https://example.com/doc.docx") is False
        assert is_crawlable_url("https://example.com/image.zip") is False

    def test_case_insensitive_filtering(self):
        """대소문자 구분 없이 필터링."""
        assert is_crawlable_url("https://example.com/DownloadFile.DO?id=123") is False
        assert is_crawlable_url("https://example.com/file.PDF") is False
        assert is_crawlable_url("https://example.com/DOWNLOAD/file") is False

    def test_query_params_with_file_extension(self):
        """쿼리 파라미터에 파일 확장자가 있어도 URL 경로 기준으로 판단."""
        # 경로는 HTML이지만 쿼리에 .pdf가 있는 경우 - 크롤링 가능
        assert is_crawlable_url("https://example.com/view?file=doc.pdf") is True

        # 경로 자체가 .pdf인 경우 - 크롤링 불가
        assert (
            is_crawlable_url("https://example.com/files/doc.pdf?download=true") is False
        )


class TestExtractContentFiltering:
    """extract_content의 URL 필터링 테스트."""

    @pytest.mark.asyncio
    async def test_extract_content_skips_download_url(self):
        """파일 다운로드 URL은 크롤링을 시도하지 않고 바로 실패 반환."""
        crawler = ContentCrawlerService()

        # 파일 다운로드 URL
        result = await crawler.extract_content(
            "https://www.moel.go.kr/common/downloadFile.do?file_seq=20200"
        )

        assert result.success is False
        assert "skipped" in result.error.lower() or "download" in result.error.lower()

    @pytest.mark.asyncio
    async def test_extract_content_skips_pdf_url(self):
        """PDF URL은 크롤링을 시도하지 않고 바로 실패 반환."""
        crawler = ContentCrawlerService()

        result = await crawler.extract_content(
            "https://example.com/documents/guide.pdf"
        )

        assert result.success is False
        assert "skipped" in result.error.lower() or "download" in result.error.lower()


class TestErrorMessages:
    """에러 메시지 명확화 테스트."""

    @pytest.mark.asyncio
    async def test_error_message_includes_reason(self):
        """에러 메시지에 실패 원인이 포함되어야 함."""
        crawler = ContentCrawlerService()

        # 존재하지 않는 URL로 테스트
        result = await crawler.extract_content(
            "https://nonexistent-domain-12345.com/page"
        )

        assert result.success is False
        # 에러 메시지가 단순히 "Fetch failed"가 아니라 원인을 포함해야 함
        assert result.error is not None
        assert len(result.error) > 10  # 의미있는 에러 메시지


# ============================================================
# 새로운 테스트: JS 렌더링 사이트, Snippet 검증, 실패 캐싱
# ============================================================


class TestJsRenderedDomain:
    """JS 렌더링 사이트 감지 테스트."""

    def test_detects_mobile_jobkorea_as_js_rendered(self):
        """m.jobkorea.co.kr은 JS 렌더링 사이트로 감지되어야 한다."""
        from app.services.search.url_filter import is_js_rendered_domain

        assert (
            is_js_rendered_domain("https://m.jobkorea.co.kr/Recruit/GI_Read/47127058")
            is True
        )

    def test_detects_kakao_story_as_js_rendered(self):
        """story.kakao.com은 JS 렌더링 사이트로 감지되어야 한다."""
        from app.services.search.url_filter import is_js_rendered_domain

        assert (
            is_js_rendered_domain("https://story.kakao.com/ch/miraclesetup/fVJXBaNJHIA")
            is True
        )

    def test_allows_official_qnet(self):
        """q-net.or.kr (공식 사이트)은 블랙리스트에 포함하지 않는다."""
        from app.services.search.url_filter import is_js_rendered_domain

        # 공식 사이트는 일부 페이지가 성공할 수 있으므로 블랙리스트 제외
        assert (
            is_js_rendered_domain("https://www.q-net.or.kr/crf005.do?id=crf00503")
            is False
        )

    def test_allows_static_blog(self):
        """tistory.com은 JS 렌더링 사이트가 아니어야 한다."""
        from app.services.search.url_filter import is_js_rendered_domain

        assert is_js_rendered_domain("https://smartinfo-tree.tistory.com/1426") is False

    def test_allows_namu_wiki(self):
        """namu.wiki는 JS 렌더링 사이트가 아니어야 한다."""
        from app.services.search.url_filter import is_js_rendered_domain

        assert is_js_rendered_domain("https://namu.wiki/w/%ED%95%AD%EA%B3%B5") is False

    def test_allows_eduwill(self):
        """eduwill.net은 JS 렌더링 사이트가 아니어야 한다."""
        from app.services.search.url_filter import is_js_rendered_domain

        assert (
            is_js_rendered_domain("https://book.eduwill.net/goods/select.action")
            is False
        )


class TestValidSnippet:
    """Snippet 품질 검증 테스트."""

    def test_rejects_empty_snippet(self):
        """빈 snippet은 유효하지 않아야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        assert is_valid_snippet("") is False
        assert is_valid_snippet(None) is False

    def test_rejects_too_short_snippet(self):
        """50자 미만 snippet은 유효하지 않아야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        assert is_valid_snippet("짧은 텍스트") is False
        assert is_valid_snippet("a" * 30) is False

    def test_accepts_valid_snippet(self):
        """50자 이상의 의미 있는 snippet은 유효해야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        valid_text = "정보처리기사 자격증은 IT 분야에서 가장 인기 있는 국가기술자격증 중 하나입니다. 시험은 필기와 실기로 나뉩니다."
        assert is_valid_snippet(valid_text) is True

    def test_rejects_loading_message(self):
        """'로딩 중' 등의 의미 없는 snippet은 유효하지 않아야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        assert is_valid_snippet("로딩 중입니다. 잠시만 기다려주세요. " * 5) is False

    def test_rejects_javascript_required_message(self):
        """JavaScript 필요 메시지는 유효하지 않아야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        assert (
            is_valid_snippet(
                "JavaScript를 활성화해주세요. 이 페이지는 JavaScript가 필요합니다." * 2
            )
            is False
        )

    def test_rejects_page_not_found_message(self):
        """페이지를 찾을 수 없음 메시지는 유효하지 않아야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        assert (
            is_valid_snippet(
                "페이지를 찾을 수 없습니다. 요청하신 페이지가 존재하지 않습니다." * 2
            )
            is False
        )

    def test_custom_min_length(self):
        """사용자 정의 최소 길이를 지원해야 한다."""
        from app.services.search.url_filter import is_valid_snippet

        text_30_chars = "가" * 30
        assert is_valid_snippet(text_30_chars, min_length=30) is True
        assert is_valid_snippet(text_30_chars, min_length=50) is False


class TestDomainFailureCache:
    """도메인별 실패 캐싱 테스트."""

    def test_initial_state_allows_all(self):
        """초기 상태에서는 모든 도메인이 허용되어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        assert cache.should_skip("https://example.com/page") is False

    def test_records_failure(self):
        """실패를 기록할 수 있어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        cache.record_failure("https://example.com/page1")

        # 1번 실패는 아직 스킵하지 않음
        assert cache.should_skip("https://example.com/page2") is False

    def test_skips_after_max_failures(self):
        """최대 실패 횟수 도달 시 해당 도메인을 스킵해야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        cache.record_failure("https://example.com/page1")
        cache.record_failure("https://example.com/page2")

        # 2번 실패 후 스킵
        assert cache.should_skip("https://example.com/page3") is True

    def test_different_domains_independent(self):
        """서로 다른 도메인은 독립적으로 카운트되어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        cache.record_failure("https://example.com/page1")
        cache.record_failure("https://example.com/page2")

        # example.com은 스킵
        assert cache.should_skip("https://example.com/page3") is True
        # other.com은 아직 허용
        assert cache.should_skip("https://other.com/page") is False

    def test_records_success(self):
        """성공을 기록하면 실패 카운트가 초기화되어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        cache.record_failure("https://example.com/page1")
        cache.record_success("https://example.com/page2")
        cache.record_failure("https://example.com/page3")

        # 성공 후 1번만 실패했으므로 아직 허용
        assert cache.should_skip("https://example.com/page4") is False

    def test_clear_cache(self):
        """캐시를 초기화할 수 있어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=2)
        cache.record_failure("https://example.com/page1")
        cache.record_failure("https://example.com/page2")

        cache.clear()

        # 초기화 후 다시 허용
        assert cache.should_skip("https://example.com/page3") is False

    def test_get_failure_count(self):
        """도메인별 실패 횟수를 조회할 수 있어야 한다."""
        from app.services.search.url_filter import DomainFailureCache

        cache = DomainFailureCache(max_failures=3)
        cache.record_failure("https://example.com/page1")
        cache.record_failure("https://example.com/page2")

        assert cache.get_failure_count("https://example.com/any") == 2
        assert cache.get_failure_count("https://other.com/any") == 0
