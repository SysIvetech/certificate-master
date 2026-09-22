"""Tests for application configuration.

TDD: Write tests FIRST, then implement the config module.
"""

import pytest


class TestSettings:
    """Test suite for Settings configuration."""

    @pytest.fixture(autouse=True)
    def setup_env_vars(self, monkeypatch):
        """Set up required environment variables for testing."""
        monkeypatch.delenv("AUTH_ENABLED", raising=False)
        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("CHROMA_HOST", "test-host")
        monkeypatch.setenv("CHROMA_PORT", "38000")
        monkeypatch.setenv("CHROMA_COLLECTION_NAME", "test-collection")

    def test_auth_disabled_by_default(self) -> None:
        """AUTH_ENABLED 기본값은 False (제한 공개 기간 동작 유지)."""
        from app.core.config import Settings

        settings = Settings(_env_file=None)

        assert settings.AUTH_ENABLED is False
        assert settings.JWT_SECRET is None

    def test_auth_enabled_requires_jwt_secret(self, monkeypatch) -> None:
        """AUTH_ENABLED=true 인데 JWT_SECRET 이 없으면 설정 로드 실패."""
        from pydantic import ValidationError

        from app.core.config import Settings

        monkeypatch.setenv("AUTH_ENABLED", "true")

        with pytest.raises(ValidationError, match="JWT_SECRET"):
            Settings(_env_file=None)

    def test_auth_enabled_with_jwt_secret(self, monkeypatch) -> None:
        """AUTH_ENABLED=true 와 JWT_SECRET 이 함께 설정되면 정상 로드."""
        from app.core.config import Settings

        monkeypatch.setenv("AUTH_ENABLED", "true")
        monkeypatch.setenv("JWT_SECRET", "c2VjcmV0")

        settings = Settings(_env_file=None)

        assert settings.AUTH_ENABLED is True
        assert settings.JWT_SECRET == "c2VjcmV0"

    def test_settings_loads_external_api_keys(self) -> None:
        """Test that Settings loads external API keys from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.OPENAI_API_KEY == "test-openai-key"

    def test_settings_loads_chroma_config(self) -> None:
        """Test that Settings loads ChromaDB configuration from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.CHROMA_HOST == "test-host"
        assert settings.CHROMA_PORT == 38000
        assert settings.CHROMA_COLLECTION_NAME == "test-collection"

    def test_settings_has_default_redis_url(self) -> None:
        """Test that Settings has default REDIS_URL."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.REDIS_URL is not None

    def test_settings_has_default_environment(self) -> None:
        """Test that Settings has default ENVIRONMENT value."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.ENVIRONMENT == "development"

    def test_settings_has_default_debug_true(self) -> None:
        """Test that Settings has DEBUG=True by default."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.DEBUG is True

    def test_get_settings_returns_settings_instance(self) -> None:
        """Test that get_settings returns a Settings instance."""
        from app.core.config import Settings, get_settings

        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        from app.core.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
