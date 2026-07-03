"""Security utilities: password hashing, JWT creation and verification.

Uses passlib with bcrypt for passwords and python-jose for JWT.
All tokens encode the subject (user ID) as a UUID string and respect
configurable expiry.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet
from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    subject:
        Unique user identifier (typically a UUID string).
    extra_claims:
        Optional additional claims to embed in the token payload.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, jti: str | None = None) -> str:
    """Create a longer-lived signed JWT refresh token.

    Parameters
    ----------
    subject:
        Unique user identifier (typically a UUID string).
    jti:
        Optional JWT ID (for revocation tracking). Generated automatically
        if not provided.
    """
    if jti is None:
        jti = create_refresh_jti()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": jti,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.

    Returns the decoded payload, or raises ``jose.JWTError`` if the
    token is expired, malformed, or signed with a different key.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


# ─── Token Helpers ────────────────────────────────────────────────────


def create_verification_token(subject: str) -> str:
    """Create a short-lived JWT for email verification.

    The token carries ``type="verify"`` and expires after
    ``VERIFICATION_TOKEN_EXPIRE_HOURS``.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS),
        "type": "verify",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_password_reset_token(subject: str) -> str:
    """Create a short-lived JWT for password reset.

    The token carries ``type="reset"`` and expires after
    ``VERIFICATION_TOKEN_EXPIRE_HOURS``.
    """
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=settings.VERIFICATION_TOKEN_EXPIRE_HOURS),
        "type": "reset",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_jti() -> str:
    """Generate a unique identifier for a refresh token (a UUID4 hex)."""
    return uuid.uuid4().hex


# ─── Cookie Helpers ────────────────────────────────────────────────────


def set_refresh_token_cookie(response: Response, token: str) -> None:
    """Set the HTTP-only refresh-token cookie on *response*.

    The cookie is restricted to the refresh endpoint path, uses
    ``SameSite=Strict``, and is flagged ``Secure`` (unless in dev
    mode where the backend runs on HTTP locally).
    """
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
        secure=not settings.is_development,  # allow HTTP in dev
        httponly=True,
        samesite="strict",
    )


def unset_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh-token cookie on *response*."""
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path=settings.REFRESH_TOKEN_COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN or None,
    )


# ─── API Key Encryption ──────────────────────────────────────────────────


def _get_fernet() -> Fernet:
    """Return a Fernet instance keyed from the app's SECRET_KEY."""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key string using Fernet symmetric encryption."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt a Fernet-encrypted API key string."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_api_key(key: str) -> str:
    """Return sk-****abcd — first 3 + last 4 chars."""
    if len(key) <= 7:
        return "****"
    return key[:3] + "****" + key[-4:]
