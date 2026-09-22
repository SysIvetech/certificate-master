"""Playwright 설정 테스트.

이 모듈은 Playwright 관련 설정이 올바르게 정의되어 있는지 테스트합니다.
"""


class TestPlaywrightConfig:
    """Playwright 설정 테스트."""

    def test_playwright_enabled_setting_exists(self):
        """PLAYWRIGHT_ENABLED 설정이 존재해야 합니다."""
        from app.core.config import Settings

        # Settings 클래스에 속성이 정의되어 있는지 확인
        assert hasattr(Settings, "__annotations__")
        assert "PLAYWRIGHT_ENABLED" in Settings.__annotations__

    def test_playwright_headless_setting_exists(self):
        """PLAYWRIGHT_HEADLESS 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "PLAYWRIGHT_HEADLESS" in Settings.__annotations__

    def test_playwright_max_browsers_setting_exists(self):
        """PLAYWRIGHT_MAX_BROWSERS 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "PLAYWRIGHT_MAX_BROWSERS" in Settings.__annotations__

    def test_playwright_max_pages_setting_exists(self):
        """PLAYWRIGHT_MAX_PAGES 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "PLAYWRIGHT_MAX_PAGES" in Settings.__annotations__

    def test_playwright_timeout_setting_exists(self):
        """PLAYWRIGHT_TIMEOUT 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "PLAYWRIGHT_TIMEOUT" in Settings.__annotations__

    def test_playwright_settings_have_defaults(self):
        """Playwright 설정에 기본값이 있어야 합니다."""
        from app.core.config import Settings

        # 기본값이 있는 필드는 model_fields에서 확인
        fields = Settings.model_fields

        # PLAYWRIGHT_ENABLED 기본값 확인
        assert "PLAYWRIGHT_ENABLED" in fields
        assert fields["PLAYWRIGHT_ENABLED"].default is True

        # PLAYWRIGHT_HEADLESS 기본값 확인
        assert "PLAYWRIGHT_HEADLESS" in fields
        assert fields["PLAYWRIGHT_HEADLESS"].default is True

        # PLAYWRIGHT_MAX_BROWSERS 기본값 확인
        assert "PLAYWRIGHT_MAX_BROWSERS" in fields
        assert fields["PLAYWRIGHT_MAX_BROWSERS"].default == 2

        # PLAYWRIGHT_MAX_PAGES 기본값 확인
        assert "PLAYWRIGHT_MAX_PAGES" in fields
        assert fields["PLAYWRIGHT_MAX_PAGES"].default == 5

        # PLAYWRIGHT_TIMEOUT 기본값 확인
        assert "PLAYWRIGHT_TIMEOUT" in fields
        assert fields["PLAYWRIGHT_TIMEOUT"].default == 30.0


class TestSearchQualityConfig:
    """검색 품질 설정 테스트."""

    def test_official_source_required_setting_exists(self):
        """SEARCH_OFFICIAL_SOURCE_REQUIRED 설정이 존재해야 합니다."""
        from app.core.config import Settings

        assert "SEARCH_OFFICIAL_SOURCE_REQUIRED" in Settings.__annotations__

    def test_official_source_required_default_is_true(self):
        """SEARCH_OFFICIAL_SOURCE_REQUIRED 기본값이 True여야 합니다."""
        from app.core.config import Settings

        fields = Settings.model_fields
        assert "SEARCH_OFFICIAL_SOURCE_REQUIRED" in fields
        assert fields["SEARCH_OFFICIAL_SOURCE_REQUIRED"].default is True
