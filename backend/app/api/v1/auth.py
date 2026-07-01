"""Authentication API router.

Implements register, login, token refresh with rotation, logout,
email verification, and password-reset flows.

All refresh-token operations use HTTP-only cookies with
``SameSite=Strict`` for XSS/CSRF protection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    DbSession,
    get_current_active_user,
    get_current_user,
    get_current_user_optional,
)
from app.core.config import settings
from app.core.rate_limiter import auth_rate_limit
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_jti,
    create_refresh_token,
    create_verification_token,
    decode_token,
    hash_password,
    set_refresh_token_cookie,
    unset_refresh_token_cookie,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
    VerifyEmailRequest,
)
from app.services.email import get_email_sender

router = APIRouter()

# ── Helpers ────────────────────────────────────────────────────────────


async def _create_refresh_token_record(
    db: AsyncSession, user: User, jti: str | None = None
) -> str:
    """Create a new refresh token, persist its record, and return the JWT string.

    Parameters
    ----------
    db:
        Database session.
    user:
        The owning user.
    jti:
        Optional JWT ID.  Generated automatically if not provided.
    """
    if jti is None:
        jti = create_refresh_jti()

    token = create_refresh_token(str(user.id), jti=jti)
    db.add(
        RefreshToken(
            user_id=user.id,
            jti=jti,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.flush()
    return token


async def _build_auth_response(
    db: AsyncSession,
    user: User,
    response: Response,
) -> AuthResponse:
    """Create a new refresh-token cookie and return the full auth payload."""
    refresh_token = await _create_refresh_token_record(db, user)
    set_refresh_token_cookie(response, refresh_token)

    access_token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/auth/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: UserCreate,
    db: DbSession,
    response: Response,
    _: None = Depends(auth_rate_limit),
) -> AuthResponse:
    """Register a new user account.

    Checks email and username uniqueness, hashes the password, creates
    a verification token stub, and returns an initial access token +
    refresh token cookie.
    """
    # ── Uniqueness checks ─────────────────────────────────────────
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or username already exists",
        )

    # ── Create user ───────────────────────────────────────────────
    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
        role=settings.DEFAULT_ROLE,
    )
    db.add(user)
    await db.flush()

    return await _build_auth_response(db, user, response)


@router.post("/auth/login", response_model=AuthResponse)
async def login(
    payload: UserLogin,
    db: DbSession,
    response: Response,
    _: None = Depends(auth_rate_limit),
) -> AuthResponse:
    """Authenticate a user by email or username.

    Returns an access token in the body and sets a refresh-token
    HTTP-only cookie.
    """
    # Lookup by email or username
    stmt = select(User).where(
        (User.email == payload.login) | (User.username == payload.login)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )

    return await _build_auth_response(db, user, response)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    db: DbSession,
    response: Response,
    body: RefreshRequest | None = None,
) -> TokenResponse:
    """Rotate the refresh token.

    Reads the existing refresh token from the HTTP-only cookie (or from
    the request body as a fallback), validates it, revokes the old token,
    and issues a new one.

    **Theft detection:** If a previously-rotated token is reused, *all*
    refresh tokens for the user are revoked.
    """
    # ── Extract token ─────────────────────────────────────────────
    raw_token: str | None = request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )
    if not raw_token and body is not None:
        raw_token = body.refresh_token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    # ── Decode JWT ────────────────────────────────────────────────
    try:
        payload = decode_token(raw_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    jti: str | None = payload.get("jti")
    user_id: str | None = payload.get("sub")
    if not jti or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed refresh token",
        )

    # ── Lookup token record ───────────────────────────────────────
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.jti == jti)
    )
    token_record = result.scalar_one_or_none()
    if token_record is None:
        # Token not in DB — treat as invalid
        unset_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    # ── Theft detection ───────────────────────────────────────────
    if token_record.is_revoked:
        # This token was already rotated — someone might have stolen it.
        # Revoke ALL refresh tokens for this user as a precaution.
        await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == token_record.user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        # Revoke all active tokens
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == token_record.user_id,
            RefreshToken.revoked_at.is_(None),
        )
        active_tokens = await db.execute(stmt)
        for t in active_tokens.scalars().all():
            t.revoked_at = datetime.now(UTC)

        unset_refresh_token_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked — all sessions terminated",
        )

    # ── Revoke old token ──────────────────────────────────────────
    token_record.revoked_at = datetime.now(UTC)

    # ── Issue new token ───────────────────────────────────────────
    new_jti = create_refresh_jti()
    new_token = create_refresh_token(user_id, jti=new_jti)
    db.add(
        RefreshToken(
            user_id=token_record.user_id,
            jti=new_jti,
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.flush()
    set_refresh_token_cookie(response, new_token)

    access_token = create_access_token(user_id)
    return TokenResponse(access_token=access_token)


@router.post("/auth/logout", response_model=MessageResponse)
async def logout(
    db: DbSession,
    response: Response,
    current_user: User | None = Depends(get_current_user_optional),
) -> MessageResponse:
    """Clear the refresh-token cookie and revoke all active refresh tokens.

    Works for both authenticated and anonymous callers (the cookie
    is cleared unconditionally).
    """
    unset_refresh_token_cookie(response)

    if current_user is not None:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in result.scalars().all():
            token.revoked_at = datetime.now(UTC)

    return MessageResponse(message="Logged out successfully")


@router.get("/auth/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Return the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/auth/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Update the current user's profile (display name, avatar URL)."""
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url

    db.add(current_user)
    await db.flush()
    return UserResponse.model_validate(current_user)


@router.put("/auth/me/password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Change the current user's password.

    Requires the current password for verification.
    """
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(payload.new_password)
    db.add(current_user)
    await db.flush()

    return MessageResponse(message="Password updated successfully")


@router.post("/auth/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: DbSession,
    _: None = Depends(auth_rate_limit),
) -> MessageResponse:
    """Request a password-reset email (stub — logs to console in dev).

    Always returns 200 to avoid user enumeration.
    """
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if user is not None:
        reset_token = create_password_reset_token(str(user.id))
        sender = get_email_sender()
        await sender.send_email(
            to=user.email,
            subject="Password Reset — Aevix",
            body=(
                f"Hi {user.display_name or user.username},\n\n"
                f"Use the following link to reset your password:\n\n"
                f"{settings.APP_NAME}/auth/reset-password?token={reset_token}\n\n"
                f"This link expires in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours."
            ),
        )

    return MessageResponse(
        message="If an account with that email exists, a reset link has been sent."
    )


@router.post("/auth/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: DbSession,
    _: None = Depends(auth_rate_limit),
) -> MessageResponse:
    """Reset a password using a valid reset token."""
    try:
        payload_data = decode_token(payload.token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if payload_data.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    user_id = payload_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed reset token",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    user.hashed_password = hash_password(payload.new_password)

    # Revoke all refresh tokens after password reset
    token_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    for t in token_result.scalars().all():
        t.revoked_at = datetime.now(UTC)

    db.add(user)
    await db.flush()

    return MessageResponse(message="Password has been reset successfully.")


@router.post("/auth/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    db: DbSession,
) -> MessageResponse:
    """Verify a user's email address using a verification token."""
    try:
        token_data = decode_token(payload.token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    if token_data.get("type") != "verify":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed verification token",
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )

    if user.is_verified:
        return MessageResponse(message="Email already verified.")

    user.is_verified = True
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    db.add(user)
    await db.flush()

    return MessageResponse(message="Email verified successfully.")


@router.post(
    "/auth/resend-verification",
    response_model=MessageResponse,
)
async def resend_verification(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """Generate a new verification token and send it via email."""
    if current_user.is_verified:
        return MessageResponse(message="Email already verified.")

    verify_token = create_verification_token(str(current_user.id))
    sender = get_email_sender()
    await sender.send_email(
        to=current_user.email,
        subject="Verify your email — Aevix",
        body=(
            f"Hi {current_user.display_name or current_user.username},\n\n"
            f"Click the link below to verify your email:\n\n"
            f"{settings.APP_NAME}/auth/verify-email?token={verify_token}\n\n"
            f"This link expires in {settings.VERIFICATION_TOKEN_EXPIRE_HOURS} hours."
        ),
    )

    return MessageResponse(
        message="Verification email sent. Check your inbox."
    )
