"""Tests for application configuration.

Validates config settings and environment.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from app.config import Settings


# Minimal valid env for Settings
_MINIMAL_ENV = {
    "DATABASE_URL": "postgresql://test:test@localhost/test",
    "AUDIT_HMAC_KEY": "0" * 32,  # 32 chars minimum
}


@pytest.fixture()
def _settings_env():
    """Patch env with minimal valid values."""
    with patch.dict("os.environ", _MINIMAL_ENV, clear=False):
        yield


class TestConfig:
    """Configuration tests."""

    def test_settings_has_database_url(self, _settings_env) -> None:
        """Settings has DATABASE_URL."""
        s = Settings()
        assert "postgresql" in s.database_url

    def test_settings_has_redis_url(self, _settings_env) -> None:
        """Settings has REDIS_URL."""
        s = Settings()
        assert "redis" in s.redis_url.lower() or "localhost" in s.redis_url

    def test_settings_has_app_env(self, _settings_env) -> None:
        """Settings has APP_ENV."""
        s = Settings()
        assert s.app_env in ("development", "staging", "production")

    def test_settings_pii_scrub_enabled(self, _settings_env) -> None:
        """Settings has PII_SCRUB_ENABLED."""
        s = Settings()
        assert s.pii_scrub_enabled is True

    def test_settings_cors_origins(self, _settings_env) -> None:
        """Settings has CORS_ORIGINS."""
        s = Settings()
        assert isinstance(s.cors_origins, list)
        assert len(s.cors_origins) > 0
