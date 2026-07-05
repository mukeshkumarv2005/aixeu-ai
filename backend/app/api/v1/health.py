import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
import redis.asyncio as aioredis

from app.api.deps import DbSession
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe: returns ok if the API process is running."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/ready")
async def readiness_check(db: DbSession) -> JSONResponse:
    """Readiness probe: checks database and Redis connectivity."""
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        logger.error("Readiness check: Database check failed", exc_info=True)

    redis_ok = False
    try:
        client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await client.ping()
        await client.close()
        redis_ok = True
    except Exception as exc:
        logger.error("Readiness check: Redis check failed", exc_info=True)

    if db_ok and redis_ok:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "ok",
                "redis": "ok",
            },
        )
    
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unready",
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    )
