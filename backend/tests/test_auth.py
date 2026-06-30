"""Comprehensive auth endpoint tests.

Covers registration, login, token refresh with rotation & theft detection,
profile management, email verification, password reset, and RBAC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import Depends
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from tests.conftest import (
    auth_header,
    create_refresh_token_record,
    create_user,
)

# ═══════════════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════════════


class TestRegister:
    async def test_success(self, client: AsyncClient, db_session: AsyncSession):
        """Register a new user returns 201 with auth response and cookie."""
        payload = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "StrongPass123!",
            "display_name": "New User",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "newuser@example.com"
        assert body["user"]["username"] == "newuser"
        assert body["user"]["display_name"] == "New User"
        assert body["user"]["role"] == "user"
        assert body["user"]["is_active"] is True
        assert body["user"]["is_verified"] is False
        # No password hash in response
        assert "hashed_password" not in body["user"]
        # Cookie set
        assert settings.REFRESH_TOKEN_COOKIE_NAME in resp.cookies
        # RefreshToken record created in DB
        result = await db_session.execute(
            select(RefreshToken).join(User).where(User.email == payload["email"])
        )
        token_records = result.scalars().all()
        assert len(token_records) >= 1

    async def test_duplicate_email(self, client: AsyncClient, db_session: AsyncSession):
        """Registering with an existing email returns 409."""
        await create_user(db_session, email="dup@example.com")
        payload = {
            "email": "dup@example.com",
            "username": "otheruser",
            "password": "StrongPass123!",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    async def test_duplicate_username(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Registering with an existing username returns 409."""
        await create_user(db_session, username="dupuser")
        payload = {
            "email": "other@example.com",
            "username": "dupuser",
            "password": "StrongPass123!",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    async def test_weak_password(self, client: AsyncClient):
        """Password shorter than 8 chars returns 422."""
        payload = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "short",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422

    async def test_missing_fields(self, client: AsyncClient):
        """Missing required fields returns 422."""
        resp = await client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422
        errors = resp.json()["detail"]
        fields_present = {e["loc"][-1] for e in errors}
        assert "email" in fields_present
        assert "username" in fields_present
        assert "password" in fields_present

    async def test_invalid_email(self, client: AsyncClient):
        """Invalid email format returns 422."""
        payload = {
            "email": "not-an-email",
            "username": "validuser",
            "password": "StrongPass123!",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# Login
# ═══════════════════════════════════════════════════════════════════════


class TestLogin:
    async def test_success_with_email(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Login with email returns auth response and cookie."""
        await create_user(db_session)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "test@example.com", "password": "strongpass123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["user"]["email"] == "test@example.com"
        assert settings.REFRESH_TOKEN_COOKIE_NAME in resp.cookies

    async def test_success_with_username(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Login with username returns auth response."""
        await create_user(db_session)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "testuser", "password": "strongpass123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["user"]["username"] == "testuser"

    async def test_wrong_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Wrong password returns 401."""
        await create_user(db_session)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "test@example.com", "password": "wrongpass123"},
        )
        assert resp.status_code == 401

    async def test_nonexistent_user(self, client: AsyncClient):
        """Non-existent user returns 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "noone@example.com", "password": "strongpass123"},
        )
        assert resp.status_code == 401

    async def test_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Inactive account returns 403."""
        await create_user(db_session, is_active=False)
        resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "test@example.com", "password": "strongpass123"},
        )
        assert resp.status_code == 403
        assert "inactive" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Token Refresh
# ═══════════════════════════════════════════════════════════════════════


class TestRefresh:
    async def test_success_via_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Refresh with a valid cookie returns a new access token and rotates the cookie."""
        user = await create_user(db_session)
        refresh_token = await create_refresh_token_record(
            db_session, user.id
        )
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, refresh_token)

        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"
        # Cookie was rotated
        new_cookie = resp.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
        assert new_cookie is not None
        assert new_cookie != refresh_token

        # Old token is now revoked
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.jti == decode_token(refresh_token)["jti"])
        )
        old_record = result.scalar_one_or_none()
        assert old_record is not None
        assert old_record.revoked_at is not None

    async def test_success_via_body(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Refresh via request body works when cookie is not available."""
        user = await create_user(db_session)
        refresh_token = await create_refresh_token_record(
            db_session, user.id
        )
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]
        # Cookie should still be set on response
        assert settings.REFRESH_TOKEN_COOKIE_NAME in resp.cookies

    async def test_missing_token(self, client: AsyncClient):
        """No refresh token → 401."""
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert "missing" in resp.json()["detail"].lower()

    async def test_invalid_token(self, client: AsyncClient):
        """Garbage token → 401."""
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, "garbage.invalid.token")
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    async def test_expired_token(self, client: AsyncClient, db_session: AsyncSession):
        """An expired refresh token returns 401."""
        user = await create_user(db_session)
        # Build an already-expired token
        from jose import jwt

        expired_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "jti": "expired-jti",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, expired_token)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401

    async def test_revoked_token(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Using a revoked token triggers theft detection — all tokens revoked."""
        user = await create_user(db_session)
        refresh_token = await create_refresh_token_record(
            db_session, user.id
        )

        # Manually revoke this token
        result = await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.jti == decode_token(refresh_token)["jti"]
            )
        )
        record = result.scalar_one_or_none()
        record.revoked_at = datetime.now(UTC)
        await db_session.flush()

        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, refresh_token)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert "revoked" in resp.json()["detail"].lower()

    async def test_wrong_token_type(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """An access token used as a refresh token returns 401."""
        user = await create_user(db_session)
        access_token = create_access_token(str(user.id))
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, access_token)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401
        assert "invalid token type" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Token Rotation / Theft Detection
# ═══════════════════════════════════════════════════════════════════════


class TestTokenRotation:
    async def test_rotation_second_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Using the OLD refresh token after a refresh returns 401 (all revoked)."""
        user = await create_user(db_session)
        refresh_token = await create_refresh_token_record(
            db_session, user.id
        )

        # First refresh — succeeds, rotates
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, refresh_token)
        resp1 = await client.post("/api/v1/auth/refresh")
        assert resp1.status_code == 200

        # Second refresh with old token — should fail (theft detection)
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, refresh_token)
        resp2 = await client.post("/api/v1/auth/refresh")
        assert resp2.status_code == 401
        assert "revoked" in resp2.json()["detail"].lower() or "terminated" in resp2.json()["detail"].lower()

    async def test_rotation_successive(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Multiple sequential refreshes all succeed."""
        user = await create_user(db_session)
        cookie_name = settings.REFRESH_TOKEN_COOKIE_NAME

        refresh_token = await create_refresh_token_record(db_session, user.id)

        for i in range(3):
            client.cookies.set(cookie_name, refresh_token)
            resp = await client.post("/api/v1/auth/refresh")
            assert resp.status_code == 200, f"Refresh {i+1} failed"
            # Grab the new cookie for next iteration
            refresh_token = resp.cookies.get(cookie_name)

        # All old tokens should be revoked
        result = await db_session.execute(select(RefreshToken))
        all_tokens = result.scalars().all()
        revoked = [t for t in all_tokens if t.revoked_at is not None]
        active = [t for t in all_tokens if not t.is_revoked]
        assert len(revoked) == 3  # Three revoked from three rotations
        assert len(active) == 1  # One active (the latest)

    async def test_theft_detection_revokes_all(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Reusing a rotated token revokes ALL tokens for that user."""
        user = await create_user(db_session)
        cookie_name = settings.REFRESH_TOKEN_COOKIE_NAME

        # Create two valid refresh tokens for the same user (parallel sessions)
        token_a = await create_refresh_token_record(db_session, user.id)
        token_b = await create_refresh_token_record(db_session, user.id)

        # Use token A — succeeds
        client.cookies.set(cookie_name, token_a)
        resp_a = await client.post("/api/v1/auth/refresh")
        assert resp_a.status_code == 200

        # Now reuse token A (stolen) — should revoke ALL tokens including B
        client.cookies.set(cookie_name, token_a)
        resp_theft = await client.post("/api/v1/auth/refresh")
        assert resp_theft.status_code == 401

        # Token B should also be revoked now
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.jti == decode_token(token_b)["jti"])
        )
        record_b = result.scalar_one_or_none()
        assert record_b is not None
        assert record_b.revoked_at is not None


# ═══════════════════════════════════════════════════════════════════════
# Profile — GET /auth/me
# ═══════════════════════════════════════════════════════════════════════


class TestGetMe:
    async def test_authenticated(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Authenticated user gets their profile."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "test@example.com"
        assert body["username"] == "testuser"
        assert body["display_name"] == "Test User"

    async def test_unauthenticated(self, client: AsyncClient):
        """No token → 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_invalid_token(self, client: AsyncClient):
        """Invalid token → 401."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# Profile — PUT /auth/me
# ═══════════════════════════════════════════════════════════════════════


class TestUpdateMe:
    async def test_update_display_name(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update display_name succeeds."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.put(
            "/api/v1/auth/me",
            headers=headers,
            json={"display_name": "Updated Name"},
        )
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Updated Name"

    async def test_update_avatar_url(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Update avatar_url succeeds."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.put(
            "/api/v1/auth/me",
            headers=headers,
            json={"avatar_url": "https://example.com/avatar.png"},
        )
        assert resp.status_code == 200
        assert resp.json()["avatar_url"] == "https://example.com/avatar.png"

    async def test_unauthorized(self, client: AsyncClient):
        """No auth → 401."""
        resp = await client.put(
            "/api/v1/auth/me",
            json={"display_name": "Hacker"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# Change Password
# ═══════════════════════════════════════════════════════════════════════


class TestChangePassword:
    async def test_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Changing password with correct current password succeeds."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.put(
            "/api/v1/auth/me/password",
            headers=headers,
            json={"current_password": "strongpass123", "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password updated successfully"

    async def test_wrong_current_password(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Wrong current password returns 400."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))
        resp = await client.put(
            "/api/v1/auth/me/password",
            headers=headers,
            json={"current_password": "wrongpass", "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    async def test_unauthenticated(self, client: AsyncClient):
        """No auth → 401."""
        resp = await client.put(
            "/api/v1/auth/me/password",
            json={"current_password": "x", "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# Email Verification
# ═══════════════════════════════════════════════════════════════════════


class TestVerifyEmail:
    async def test_full_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Register → verify token → confirmed verified."""
        user = await create_user(db_session, is_verified=False)
        verify_token = create_verification_token(str(user.id))

        resp = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": verify_token},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Email verified successfully."

        # Confirm user is verified in DB
        result = await db_session.execute(
            select(User).where(User.id == user.id)
        )
        updated_user = result.scalar_one_or_none()
        assert updated_user is not None
        assert updated_user.is_verified is True

    async def test_invalid_token(self, client: AsyncClient):
        """Bad token → 400."""
        resp = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": "totally.invalid.token"},
        )
        assert resp.status_code == 400

    async def test_wrong_token_type(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Using an access token as a verification token → 400."""
        user = await create_user(db_session)
        access_token = create_access_token(str(user.id))
        resp = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": access_token},
        )
        assert resp.status_code == 400
        assert "invalid token type" in resp.json()["detail"].lower()

    async def test_already_verified(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Verify already-verified user → 200 with info message."""
        user = await create_user(db_session, is_verified=True)
        verify_token = create_verification_token(str(user.id))

        resp = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": verify_token},
        )
        assert resp.status_code == 200
        assert "already verified" in resp.json()["message"].lower()


class TestResendVerification:
    async def test_resend_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Resend verification email returns 200."""
        user = await create_user(db_session, is_verified=False)
        headers = auth_header(str(user.id))

        with patch("app.api.v1.auth.get_email_sender") as mock_sender_factory:
            mock_sender = AsyncMock()
            mock_sender_factory.return_value = mock_sender
            resp = await client.post(
                "/api/v1/auth/resend-verification",
                headers=headers,
            )
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()

    async def test_already_verified(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Already verified user gets info message."""
        user = await create_user(db_session, is_verified=True)
        headers = auth_header(str(user.id))
        resp = await client.post(
            "/api/v1/auth/resend-verification",
            headers=headers,
        )
        assert resp.status_code == 200
        assert "already verified" in resp.json()["message"].lower()

    async def test_unauthenticated(self, client: AsyncClient):
        """No auth → 401."""
        resp = await client.post("/api/v1/auth/resend-verification")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# Password Reset
# ═══════════════════════════════════════════════════════════════════════


class TestForgotPassword:
    async def test_returns_200_always(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Forgot password returns 200 even for non-existent email (no enumeration)."""
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()

    async def test_with_valid_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """With a valid user, sends email (stub logs to console)."""
        await create_user(db_session)
        with patch("app.api.v1.auth.get_email_sender") as mock_sender_factory:
            mock_sender = AsyncMock()
            mock_sender_factory.return_value = mock_sender
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "test@example.com"},
            )
        assert resp.status_code == 200
        mock_sender.send_email.assert_called_once()


class TestResetPassword:
    async def test_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Valid reset token allows password change."""
        user = await create_user(db_session)
        reset_token = create_password_reset_token(str(user.id))

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()

        # Can login with new password
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"login": "test@example.com", "password": "NewStrongPass456!"},
        )
        assert login_resp.status_code == 200

        # Old password no longer works
        login_old = await client.post(
            "/api/v1/auth/login",
            json={"login": "test@example.com", "password": "strongpass123"},
        )
        assert login_old.status_code == 401

    async def test_invalid_token(self, client: AsyncClient):
        """Bad reset token → 400."""
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid.token.here", "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 400

    async def test_wrong_token_type(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Access token used as reset token → 400."""
        user = await create_user(db_session)
        access_token = create_access_token(str(user.id))
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": access_token, "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 400

    async def test_nonexistent_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Reset token for deleted user → 400."""
        # Create a user, get a reset token, delete from DB
        user = await create_user(db_session)
        reset_token = create_password_reset_token(str(user.id))
        await db_session.delete(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": "NewStrongPass456!"},
        )
        assert resp.status_code == 400
        assert "user not found" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════
# Logout
# ═══════════════════════════════════════════════════════════════════════


class TestLogout:
    async def test_logout_revokes_tokens(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Logout revokes all active refresh tokens for the user."""
        user = await create_user(db_session)
        headers = auth_header(str(user.id))

        # Create a couple of refresh tokens
        await create_refresh_token_record(db_session, user.id)
        await create_refresh_token_record(db_session, user.id)

        resp = await client.post("/api/v1/auth/logout", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Logged out successfully"

        # All tokens should be revoked
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        tokens = result.scalars().all()
        for t in tokens:
            assert t.revoked_at is not None, f"Token {t.jti} was not revoked"

    async def test_logout_anonymous(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Unauthenticated logout still clears cookie and returns 200."""
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 200

    async def test_refresh_after_logout_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Using a refresh token after logout returns 401."""
        user = await create_user(db_session)
        refresh_token = await create_refresh_token_record(
            db_session, user.id
        )

        # Logout (authenticated)
        headers = auth_header(str(user.id))
        await client.post("/api/v1/auth/logout", headers=headers)

        # Try to use the old refresh token
        client.cookies.set(settings.REFRESH_TOKEN_COOKIE_NAME, refresh_token)
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════
# RBAC — Role-Based Access Control
# ═══════════════════════════════════════════════════════════════════════


class TestRBAC:
    async def test_user_default_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """New users default to the 'user' role."""
        payload = {
            "email": "rbtest@example.com",
            "username": "rbtest",
            "password": "StrongPass123!",
        }
        resp = await client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 201
        assert resp.json()["user"]["role"] == "user"

    async def test_require_role_allows_admin(
        self, client: AsyncClient, db_session: AsyncSession, app
    ):
        """Admin user can access admin-only endpoints."""
        from app.api.deps import require_role

        # Register a test endpoint that requires "admin"
        @app.get("/api/v1/admin/test")
        async def _admin_test(
            user: User = Depends(require_role("admin")),  # noqa: B008
        ):
            return {"ok": True}

        admin = await create_user(db_session, role="admin")
        headers = auth_header(str(admin.id))
        resp = await client.get("/api/v1/admin/test", headers=headers)
        assert resp.status_code == 200

    async def test_require_role_denies_user(
        self, client: AsyncClient, db_session: AsyncSession, app
    ):
        """Regular user cannot access admin-only endpoints."""
        from app.api.deps import require_role

        @app.get("/api/v1/admin/deny")
        async def _admin_deny(
            user: User = Depends(require_role("admin")),  # noqa: B008
        ):
            return {"ok": True}

        user = await create_user(db_session, role="user")
        headers = auth_header(str(user.id))
        resp = await client.get("/api/v1/admin/deny", headers=headers)
        assert resp.status_code == 403
