"""Test fixtures — async SQLite in-memory, dependency overrides, test client."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles

# Allow PostgreSQL-specific JSONB to work with SQLite in tests.
# SQLAlchemy's generic JSON maps to TEXT on SQLite, which is what we want.
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"

from app.api.deps import get_db
from app.core.security import (
    create_access_token,
    create_refresh_jti,
    create_refresh_token,
    hash_password,
)
from app.main import create_app
from app.models import Base
from app.models.refresh_token import RefreshToken
from app.models.user import User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, Any, None]:
    """Create a single event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create a shared in-memory SQLite engine for the test session.

    Each connection gets its own private in-memory database because
    SQLite ``:memory:`` is per-connection.  Tables are created per-test
    in ``db_session`` instead of here.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session for each test, rolled back on teardown.

    Creates all tables on the new connection (necessary because SQLite
    in-memory databases are private to each connection).  The tables are
    created and committed in a separate transaction, then a new transaction
    is begun for the test — the rollback undoes test data but leaves DDL.
    """
    connection = await async_engine.connect()
    async with connection.begin():
        await connection.run_sync(Base.metadata.create_all)
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def app(db_session: AsyncSession) -> FastAPI:
    """Return the FastAPI app with ``get_db`` overridden to the test session."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application = create_app()
    application.dependency_overrides[get_db] = _override_get_db
    return application


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async test client against the app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Factory helpers ────────────────────────────────────────────────────


async def create_user(  # noqa: PLR0913
    db_session: AsyncSession,
    *,
    email: str = "test@example.com",
    username: str = "testuser",
    password: str = "strongpass123",
    display_name: str | None = "Test User",
    role: str = "user",
    is_active: bool = True,
    is_verified: bool = False,
) -> User:
    """Create a user in the database and return the model instance."""
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        display_name=display_name,
        role=role,
        is_active=is_active,
        is_verified=is_verified,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def create_refresh_token_record(
    db_session: AsyncSession,
    user_id: uuid.UUID,
) -> str:
    """Create a refresh token record and return the JWT string."""
    from datetime import UTC, datetime, timedelta

    from app.core.config import settings

    jti = create_refresh_jti()
    token = create_refresh_token(str(user_id), jti=jti)
    db_session.add(
        RefreshToken(
            user_id=user_id,
            jti=jti,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db_session.flush()
    return token


def auth_header(user_id: str) -> dict[str, str]:
    """Build an Authorization header with a valid access token."""
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}
