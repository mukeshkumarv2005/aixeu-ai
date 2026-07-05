"""Unit tests for the Redis-based rate limiter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request

from app.core import rate_limiter
from app.core.config import settings


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset module-level rate limiter state between tests."""
    rate_limiter._redis = None
    rate_limiter._redis_available = True
    yield


@pytest.mark.asyncio
async def test_get_redis_success():
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_from_url.return_value = mock_redis

        r = await rate_limiter._get_redis()
        assert r is mock_redis
        assert rate_limiter._redis_available is True
        mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_get_redis_unavailable():
    with patch("redis.asyncio.from_url") as mock_from_url:
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))
        mock_from_url.return_value = mock_redis

        r = await rate_limiter._get_redis()
        assert r is None
        assert rate_limiter._redis_available is False


@pytest.mark.asyncio
async def test_get_redis_cached_unavailable():
    rate_limiter._redis_available = False
    r = await rate_limiter._get_redis()
    assert r is None


@pytest.mark.asyncio
async def test_is_rate_limited_no_redis():
    rate_limiter._redis_available = False
    res = await rate_limiter.is_rate_limited("key")
    assert res is False


@pytest.mark.asyncio
async def test_is_rate_limited_first_request():
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()

    with patch("app.core.rate_limiter._get_redis", return_value=mock_redis):
        res = await rate_limiter.is_rate_limited("test-key", max_requests=5, window_seconds=10)
        assert res is False
        mock_redis.incr.assert_called_once_with("test-key")
        mock_redis.expire.assert_called_once_with("test-key", 10)


@pytest.mark.asyncio
async def test_is_rate_limited_subsequent_request():
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=3)
    mock_redis.expire = AsyncMock()

    with patch("app.core.rate_limiter._get_redis", return_value=mock_redis):
        res = await rate_limiter.is_rate_limited("test-key", max_requests=5, window_seconds=10)
        assert res is False
        mock_redis.incr.assert_called_once_with("test-key")
        mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_is_rate_limited_exceeded():
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=6)
    mock_redis.expire = AsyncMock()

    with patch("app.core.rate_limiter._get_redis", return_value=mock_redis):
        res = await rate_limiter.is_rate_limited("test-key", max_requests=5, window_seconds=10)
        assert res is True
        mock_redis.incr.assert_called_once_with("test-key")
        mock_redis.expire.assert_not_called()


@pytest.mark.asyncio
async def test_is_rate_limited_redis_exception():
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("Redis error"))

    with patch("app.core.rate_limiter._get_redis", return_value=mock_redis):
        res = await rate_limiter.is_rate_limited("test-key")
        assert res is False


@pytest.mark.asyncio
async def test_auth_rate_limit_disabled():
    with patch.object(settings, "AUTH_RATE_LIMIT_ENABLED", False):
        mock_request = MagicMock(spec=Request)
        await rate_limiter.auth_rate_limit(mock_request)


@pytest.mark.asyncio
async def test_auth_rate_limit_allowed():
    with patch.object(settings, "AUTH_RATE_LIMIT_ENABLED", True):
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        with patch("app.core.rate_limiter.is_rate_limited", return_value=False) as mock_check:
            await rate_limiter.auth_rate_limit(mock_request)
            mock_check.assert_called_once_with(
                "rl:auth:192.168.1.1",
                max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
            )


@pytest.mark.asyncio
async def test_auth_rate_limit_blocked():
    with patch.object(settings, "AUTH_RATE_LIMIT_ENABLED", True):
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        mock_request.client = None

        with patch("app.core.rate_limiter.is_rate_limited", return_value=True) as mock_check:
            with pytest.raises(HTTPException) as exc_info:
                await rate_limiter.auth_rate_limit(mock_request)
            assert exc_info.value.status_code == 429
            assert "Too many requests" in exc_info.value.detail
            mock_check.assert_called_once_with(
                "rl:auth:10.0.0.1",
                max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
                window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
            )
