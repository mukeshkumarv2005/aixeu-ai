"""Aevix FastAPI application entrypoint.

Initialises the ASGI application, registers middleware (CORS,
trusted-host), mounts versioned API routers, and manages the
lifespan lifecycle (background tasks).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, health
from app.core.config import settings
from app.core.tasks import cleanup_expired_refresh_tokens

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — starts / cancels background tasks."""
    cleanup_task = None
    if settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES > 0:
        logger.info(
            "Starting expired refresh-token cleanup every %d min",
            settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES,
        )
        cleanup_task = asyncio.create_task(
            cleanup_expired_refresh_tokens(
                settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES,
            ),
        )

    yield  # application runs here

    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=settings.BACKEND_CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])

    return app


app = create_app()
