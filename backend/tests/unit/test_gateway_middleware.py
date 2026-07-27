import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from app.middleware.gateway import APIGatewayMiddleware
from app.core.config import get_settings

def test_production_startup_check_raises_when_redis_unset():
    """Assert that initializing APIGatewayMiddleware in production with REDIS_URL unset raises RuntimeError."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    orig_redis = getattr(settings, "REDIS_URL", None)

    try:
        settings.ENVIRONMENT = "production"
        settings.REDIS_URL = ""

        app = FastAPI()
        with pytest.raises(RuntimeError) as exc_info:
            APIGatewayMiddleware(app)

        assert "Production boot failed: REDIS_URL is required" in str(exc_info.value)
    finally:
        settings.ENVIRONMENT = orig_env
        settings.REDIS_URL = orig_redis


def test_production_startup_check_raises_when_redis_unreachable():
    """Assert that initializing APIGatewayMiddleware in production with unreachable Redis raises RuntimeError."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT
    orig_redis = getattr(settings, "REDIS_URL", None)

    try:
        settings.ENVIRONMENT = "production"
        settings.REDIS_URL = "redis://nonexistent-redis-host:6379/0"

        app = FastAPI()
        with patch("redis.Redis.from_url") as mock_from_url:
            mock_instance = MagicMock()
            mock_instance.ping.side_effect = Exception("Connection refused")
            mock_from_url.return_value = mock_instance

            with pytest.raises(RuntimeError) as exc_info:
                APIGatewayMiddleware(app)

            assert "unreachable" in str(exc_info.value)
    finally:
        settings.ENVIRONMENT = orig_env
        settings.REDIS_URL = orig_redis


def test_development_startup_allows_in_memory_fallback():
    """Assert that initializing APIGatewayMiddleware in development mode succeeds with in-memory rate limiting."""
    settings = get_settings()
    orig_env = settings.ENVIRONMENT

    try:
        settings.ENVIRONMENT = "development"
        app = FastAPI()
        middleware = APIGatewayMiddleware(app)
        assert middleware._max_requests == settings.RATE_LIMIT_REQUESTS
    finally:
        settings.ENVIRONMENT = orig_env
