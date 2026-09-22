"""URL 필터 확장 테스트.

이 모듈은 Playwright 대상 사이트가 올바르게 필터링되는지 테스트합니다.
"""


class TestPlaywrightDomainDetection:
    """Playwright 필요 도메인 감지 테스트."""

    def test_is_playwright_required_exists(self):
        """is_playwright_required 함수가 존재해야 합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert callable(is_playwright_required)

    def test_jobkorea_requires_playwright(self):
        """jobkorea.co.kr은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        # 다양한 jobkorea URL 패턴
        assert is_playwright_required("https://www.jobkorea.co.kr/job/123") is True
        assert is_playwright_required("https://m.jobkorea.co.kr/job/123") is True
        assert is_playwright_required("https://jobkorea.co.kr/recruit/456") is True

    def test_saramin_requires_playwright(self):
        """saramin.co.kr은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://www.saramin.co.kr/job/123") is True
        assert is_playwright_required("https://m.saramin.co.kr/zf_user/123") is True
        assert is_playwright_required("https://saramin.co.kr/recruit/456") is True

    def test_wanted_requires_playwright(self):
        """wanted.co.kr은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://www.wanted.co.kr/wd/123") is True
        assert is_playwright_required("https://wanted.co.kr/cv/456") is True

    def test_incruit_requires_playwright(self):
        """incruit.com은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://www.incruit.com/job/123") is True
        assert is_playwright_required("https://job.incruit.com/entry/456") is True

    def test_kakao_story_requires_playwright(self):
        """story.kakao.com은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://story.kakao.com/abc/123") is True

    def test_brunch_requires_playwright(self):
        """brunch.co.kr은 Playwright가 필요합니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://brunch.co.kr/@user/123") is True

    def test_regular_sites_do_not_require_playwright(self):
        """일반 사이트는 Playwright가 필요하지 않습니다."""
        from app.services.search.url_filter import is_playwright_required

        assert is_playwright_required("https://example.com") is False
        assert is_playwright_required("https://blog.naver.com/abc") is False
        assert is_playwright_required("https://tistory.com/123") is False
        assert is_playwright_required("https://google.com/search") is False

    def test_qnet_can_be_configured(self):
        """Q-Net은 설정에 따라 Playwright 사용 여부가 결정됩니다."""
        from app.services.search.url_filter import is_playwright_required

        # Q-Net은 기본적으로 Trafilatura로 처리 가능하지만
        # 일부 동적 페이지는 Playwright가 필요할 수 있음
        # 현재는 Trafilatura 우선 (False)
        result = is_playwright_required("https://www.q-net.or.kr/crf005.do")
        assert isinstance(result, bool)


class TestPlaywrightDomainList:
    """Playwright 필요 도메인 목록 테스트."""

    def test_playwright_domains_constant_exists(self):
        """PLAYWRIGHT_DOMAINS 상수가 존재해야 합니다."""
        from app.services.search.url_filter import PLAYWRIGHT_DOMAINS

        assert isinstance(PLAYWRIGHT_DOMAINS, set)

    def test_playwright_domains_contains_job_sites(self):
        """채용 사이트가 PLAYWRIGHT_DOMAINS에 포함되어야 합니다."""
        from app.services.search.url_filter import PLAYWRIGHT_DOMAINS

        job_sites = {"jobkorea.co.kr", "saramin.co.kr", "wanted.co.kr", "incruit.com"}

        for site in job_sites:
            assert site in PLAYWRIGHT_DOMAINS, f"{site} should be in PLAYWRIGHT_DOMAINS"

    def test_playwright_domains_contains_social_sites(self):
        """소셜/커뮤니티 사이트가 PLAYWRIGHT_DOMAINS에 포함되어야 합니다."""
        from app.services.search.url_filter import PLAYWRIGHT_DOMAINS

        social_sites = {"story.kakao.com", "brunch.co.kr"}

        for site in social_sites:
            assert site in PLAYWRIGHT_DOMAINS, f"{site} should be in PLAYWRIGHT_DOMAINS"


class TestJsRenderedDomainBackwardCompatibility:
    """기존 is_js_rendered_domain과의 호환성 테스트."""

    def test_is_js_rendered_domain_still_works(self):
        """기존 is_js_rendered_domain 함수가 계속 작동해야 합니다."""
        from app.services.search.url_filter import is_js_rendered_domain

        # 기존 동작 유지
        assert is_js_rendered_domain("https://m.jobkorea.co.kr/job/123") is True
        assert is_js_rendered_domain("https://example.com") is False

    def test_is_playwright_required_includes_js_rendered(self):
        """is_playwright_required는 is_js_rendered_domain을 포함해야 합니다."""
        from app.services.search.url_filter import (
            is_js_rendered_domain,
            is_playwright_required,
        )

        # JS 렌더링 사이트는 모두 Playwright 필요
        test_urls = [
            "https://m.jobkorea.co.kr/job/123",
            "https://m.saramin.co.kr/job/456",
            "https://story.kakao.com/abc",
        ]

        for url in test_urls:
            if is_js_rendered_domain(url):
                assert is_playwright_required(url) is True
