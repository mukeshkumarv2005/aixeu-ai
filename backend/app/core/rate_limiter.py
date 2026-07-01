"""Redis-based rate limiter for authentication endpoints.

Provides a FastAPI dependency that rate-limits requests by client IP
using a fixed-window counter (INCR + EXPIRE).

Gracefully degrades when Redis is unavailable — requests are allowed
through and a warning is logged.

Usage::

    from app.core.rate_limiter import auth_rate_limit

    @router.post("/auth/login")
    async def login(
        payload: UserLogin,
        db: DbSession,
        response: Response,
        _: None = Depends(auth_rate_limit),
    ) -> AuthResponse:
        ...
"""

from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Module-level Redis client (lazy‑initialised, cached on success)
_redis = None
_redis_available = True


async def _get_redis():
    """Return the async Redis client or ``None`` if unavailable.

    The first failed connection permanently marks Redis as unavailable
    for the lifetime of the process, avoiding repeated timeouts.
    """
    global _redis, _redis_available  # noqa: PLW0603

    if not _redis_available:
        return None

    if _redis is None:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            await _redis.ping()
        except Exception as exc:
            logger.warning("Redis unavailable — rate limiting disabled (%s)", exc)
            _redis_available = False
            return None

    return _redis


async def is_rate_limited(
    key: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> bool:
    """Check whether *key* has exceeded the allowed request rate.

    Returns ``True`` when the caller should be blocked, ``False`` if
    allowed.  Gracefully degrades to ``False`` when Redis is unavailable.
    """
    redis = await _get_redis()
    if redis is None:
        return False

    try:
        current = await redis.incr(key)
        if current == 1:
            await redis.expire(key, window_seconds)
        return current > max_requests
    except Exception as exc:
        logger.warning("Rate-limit check failed — allowing request (%s)", exc)
        return False  # fail open


async def auth_rate_limit(request: Request) -> None:
    """FastAPI dependency — rate-limit auth endpoints by client IP.

    Raises ``429 Too Many Requests`` when the limit is exceeded.
    """
    if not settings.AUTH_RATE_LIMIT_ENABLED:
        return

    # Try the X-Forwarded-For header (reverse proxy) first; fall back to
    # the direct remote address.
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (
        request.client.host if request.client else "127.0.0.1"
    )

    key = f"rl:auth:{client_ip}"

    blocked = await is_rate_limited(
        key,
        max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
    )

    if blocked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
