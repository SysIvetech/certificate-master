"""BrowserPool 테스트.

이 모듈은 Playwright 브라우저 인스턴스 풀 관리를 테스트합니다.
"""

import pytest


class TestBrowserPoolBasic:
    """BrowserPool 기본 기능 테스트."""

    def test_browser_pool_can_be_imported(self):
        """BrowserPool을 임포트할 수 있어야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        assert BrowserPool is not None

    def test_browser_pool_initialization(self):
        """BrowserPool이 올바르게 초기화되어야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool(max_browsers=2, max_pages_per_browser=5)

        assert pool.max_browsers == 2
        assert pool.max_pages_per_browser == 5
        assert pool.max_concurrent == 10  # 2 * 5

    def test_browser_pool_default_values(self):
        """BrowserPool이 기본값으로 초기화되어야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool()

        assert pool.max_browsers == 2
        assert pool.max_pages_per_browser == 5

    def test_browser_pool_has_semaphore(self):
        """BrowserPool이 동시성 제어를 위한 세마포어를 가져야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool(max_browsers=2, max_pages_per_browser=3)

        # 세마포어 속성 확인
        assert hasattr(pool, "_semaphore") or hasattr(pool, "semaphore")


class TestBrowserPoolAsync:
    """BrowserPool 비동기 기능 테스트."""

    @pytest.mark.asyncio
    async def test_get_page_returns_page_context(self):
        """get_page가 페이지 컨텍스트를 반환해야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool()

        # Playwright가 설치되어 있지 않으면 건너뜀
        try:
            async with pool.get_page() as page:
                assert page is not None
        except ImportError:
            pytest.skip("Playwright not installed")
        finally:
            await pool.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_releases_resources(self):
        """cleanup이 브라우저 리소스를 해제해야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool()

        # cleanup 호출 후 상태 확인
        await pool.cleanup()

        # 브라우저가 해제되었는지 확인
        assert pool._browser is None or not pool._browser


class TestBrowserPoolSingleton:
    """BrowserPool 싱글턴 테스트."""

    def test_get_browser_pool_returns_instance(self):
        """get_browser_pool이 인스턴스를 반환해야 합니다."""
        from app.services.search.crawler.browser_pool import get_browser_pool

        pool = get_browser_pool()

        assert pool is not None

    def test_get_browser_pool_returns_same_instance(self):
        """get_browser_pool이 동일한 인스턴스를 반환해야 합니다."""
        from app.services.search.crawler.browser_pool import (
            get_browser_pool,
            reset_browser_pool,
        )

        # 싱글턴 리셋 후 테스트
        reset_browser_pool()

        pool1 = get_browser_pool()
        pool2 = get_browser_pool()

        assert pool1 is pool2

    @pytest.mark.asyncio
    async def test_reset_browser_pool_clears_singleton(self):
        """reset_browser_pool이 싱글턴을 리셋해야 합니다."""
        from app.services.search.crawler.browser_pool import (
            get_browser_pool,
            reset_browser_pool,
        )

        pool1 = get_browser_pool()
        reset_browser_pool()
        pool2 = get_browser_pool()

        assert pool1 is not pool2


class TestBrowserPoolConfig:
    """BrowserPool 설정 테스트."""

    def test_browser_pool_respects_config(self):
        """BrowserPool이 config 설정을 존중해야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool(
            max_browsers=3,
            max_pages_per_browser=4,
            headless=False,
            timeout=60.0,
        )

        assert pool.max_browsers == 3
        assert pool.max_pages_per_browser == 4
        assert pool.headless is False
        assert pool.timeout == 60.0

    def test_browser_pool_max_concurrent_calculation(self):
        """BrowserPool의 max_concurrent가 올바르게 계산되어야 합니다."""
        from app.services.search.crawler.browser_pool import BrowserPool

        pool = BrowserPool(max_browsers=4, max_pages_per_browser=3)

        assert pool.max_concurrent == 12  # 4 * 3
