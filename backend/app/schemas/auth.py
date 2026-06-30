"""Auth-related Pydantic schemas for request validation and response serialisation."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ─── Request Schemas ──────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Registration payload."""

    email: EmailStr = Field(..., max_length=255)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str | None = Field(None, min_length=1, max_length=100)


class UserLogin(BaseModel):
    """Login payload — accepts *email* or *username* in the ``login`` field."""

    login: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)


class UserUpdate(BaseModel):
    """Profile-update payload (all fields optional)."""

    display_name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = Field(None, max_length=512)


class ChangePasswordRequest(BaseModel):
    """Payload for changing the current user's password."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """Payload for requesting a password-reset email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload for resetting a password with a token."""

    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Payload for email verification (token from query or body)."""

    token: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    """Payload for refresh-token rotation (used when cookie is unavailable)."""

    refresh_token: str = Field(..., min_length=1)


# ─── Response Schemas ────────────────────────────────────────────────


class UserResponse(BaseModel):
    """Public user profile — never exposes the password hash."""

    id: UUID
    email: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response returned on login / refresh."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900)  # 15 min in seconds


class AuthResponse(BaseModel):
    """Combined token + user response for login/register flows."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default=900)
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
