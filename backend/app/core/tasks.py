"""Background tasks — periodic DB cleanup, etc.

CURRENT TASKS
-------------
* ``cleanup_expired_refresh_tokens`` — deletes ``RefreshToken`` records whose
  ``expires_at`` is in the past.  Designed to run as a long-lived asyncio task
  inside the FastAPI lifespan.

Usage::

    # In ``main.py``:
    from contextlib import asynccontextmanager
    from app.core.tasks import cleanup_expired_refresh_tokens

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES > 0:
            task = asyncio.create_task(
                cleanup_expired_refresh_tokens(settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES)
            )
        yield
        if settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES > 0:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import delete

from app.database import AsyncSessionFactory
from app.models.refresh_token import RefreshToken

logger = logging.getLogger(__name__)


async def cleanup_expired_refresh_tokens(interval_minutes: int) -> None:
    """Periodically delete expired refresh tokens.

    Runs forever (or until cancelled).  Each iteration deletes all
    ``RefreshToken`` rows whose ``expires_at < now()``, committing
    the deletion.

    Parameters
    ----------
    interval_minutes:
        Sleep interval between iterations in minutes.
    """
    while True:
        try:
            async with AsyncSessionFactory() as session:
                now = datetime.now(UTC)
                result = await session.execute(
                    delete(RefreshToken).where(RefreshToken.expires_at < now)
                )
                await session.commit()
                if result.rowcount > 0:
                    logger.info(
                        "Cleaned up expired refresh tokens",
                        extra={"count": result.rowcount},
                    )
        except Exception as exc:
            logger.warning(
                "Refresh-token cleanup iteration failed",
                exc_info=True,
                extra={"error": str(exc)},
            )

        await asyncio.sleep(interval_minutes * 60)
