"""FastAPI dependencies: database session, authenticated user, RBAC guards.

Typical usage::

    @router.get("/me")
    async def get_me(user: User = Depends(get_current_active_user)):
        ...

    @router.get("/admin")
    async def admin_only(user: User = Depends(require_role("admin"))):
        ...
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db as _get_db
from app.models.user import User

# Re-export for convenience
get_db = _get_db
DbSession = Annotated[AsyncSession, Depends(get_db)]

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> User:
    """Validate the Bearer token and return the authenticated user.

    Raises ``401`` if the token is missing, expired, malformed, or
    the user no longer exists.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str | None = payload.get("sub")
    token_type: str | None = payload.get("type")
    if user_id is None or token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user, ensuring the account is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )
    return current_user


def require_role(required: str) -> type:
    """Dependency factory — returns a dependency that checks the user's role.

    Example::

        @router.get("/admin")
        async def admin_dashboard(
            user: User = Depends(require_role("admin")),
        ):
            ...

    The check grants access if the user's role is **at least** the
    required level (i.e. ``admin >= user`` in priority order).
    """

    async def _role_checker(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        role_hierarchy = {"user": 0, "admin": 1}
        if role_hierarchy.get(current_user.role, -1) < role_hierarchy.get(
            required, 0
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _role_checker


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like ``get_current_user`` but returns ``None`` instead of 401.

    Useful for endpoints that behave differently for authenticated
    vs anonymous users.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        return None

    user_id = payload.get("sub")
    if user_id is None or payload.get("type") != "access":
        return None

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    return result.scalar_one_or_none()
