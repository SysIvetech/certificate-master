"""Tests for application configuration.

TDD: Write tests FIRST, then implement the config module.
"""

import pytest


class TestSettings:
    """Test suite for Settings configuration."""

    @pytest.fixture(autouse=True)
    def setup_env_vars(self, monkeypatch):
        """Set up required environment variables for testing."""
        monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "test-anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test-service-key")
        monkeypatch.setenv(
            "SUPABASE_DB_URL", "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("CHROMA_HOST", "test-host")
        monkeypatch.setenv("CHROMA_PORT", "38000")
        monkeypatch.setenv("CHROMA_COLLECTION_NAME", "test-collection")

    def test_settings_loads_supabase_url(self) -> None:
        """Test that Settings loads SUPABASE_URL from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.SUPABASE_URL == "http://localhost:54321"

    def test_settings_loads_supabase_keys(self) -> None:
        """Test that Settings loads Supabase keys from environment."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.SUPABASE_ANON_KEY == "test-anon-key"
        assert settings.SUPABASE_SERVICE_ROLE_KEY == "test-service-key"

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
