"""Aevix FastAPI application entrypoint.

Initialises the ASGI application, registers middleware (CORS,
trusted-host), mounts versioned API routers, and manages the
lifespan lifecycle (background tasks).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import agents, auth, chat, dashboard, documents, health, knowledge, search, settings as settings_router, storage, task_ai, tasks
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import setup_logging
from app.core.tasks import cleanup_expired_refresh_tokens

# Initialize structured logging
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — starts / cancels background tasks."""
    cleanup_task = None
    if settings.REFRESH_TOKEN_CLEANUP_INTERVAL_MINUTES > 0 and not settings.ASYNC_WORKERS:
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

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        return response

    # ── Exception handlers ──────────────────────────────────────
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error occurred")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error occurred. Please try again later."},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                headers=getattr(exc, "headers", None),
                content={"detail": exc.detail},
            )
        logger.exception("Unhandled server error occurred")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # ── Routers ────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
    app.include_router(storage.router, prefix="/api/v1", tags=["Storage"])
    app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
    app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
    app.include_router(knowledge.router, prefix="/api/v1", tags=["Knowledge Base"])
    app.include_router(tasks.router, prefix="/api/v1", tags=["Tasks"])
    app.include_router(task_ai.router, prefix="/api/v1", tags=["AI Tasks"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(agents.router, prefix="/api/v1", tags=["AI Agents"])
    app.include_router(settings_router.router, prefix="/api/v1", tags=["Settings"])

    return app


app = create_app()
