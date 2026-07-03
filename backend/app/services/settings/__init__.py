"""Settings service — user preferences, API providers, sessions.

The ``SettingsService`` follows the same service-layer pattern as
``AgentService`` and ``TaskService``:

- Class takes ``AsyncSession``
- Raises ``AppException`` subclasses for 4xx errors
- Uses helpers for fetch-or-raise patterns
- Returns Pydantic response objects
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.exceptions import AppException
from app.core.security import (
    decrypt_api_key,
    encrypt_api_key,
    hash_password,
    verify_password,
)
from app.models.settings import ApiProviderConfig, UserSession, UserSettings
from app.models.user import User
from app.schemas.settings import (
    ACCENT_COLORS,
    AI_PROVIDERS,
    DENSITY_OPTIONS,
    THEME_OPTIONS,
    ApiProviderCreate,
    ApiProviderResponse,
    ApiProviderUpdate,
    PasswordChangeRequest,
    SettingsExportResponse,
    SettingsImport,
    UserSessionResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
# ── Exceptions ─────────────────────────────────────────────────────────────────


class SettingsNotFound(AppException):
    def __init__(self) -> None:
        super().__init__(status_code=404, detail="User settings not found")


class ProviderNotFound(AppException):
    def __init__(self, provider_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"API provider {provider_id} not found")


class ProviderAlreadyExists(AppException):
    def __init__(self, provider: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"API provider '{provider}' is already configured",
        )


class SessionNotFound(AppException):
    def __init__(self, session_id: uuid.UUID) -> None:
        super().__init__(
            status_code=404, detail=f"Session {session_id} not found"
        )


class CannotRevokeCurrentSession(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=400,
            detail="Cannot revoke your current session via this endpoint. "
            "Use the 'revoke all other sessions' endpoint or sign out.",
        )


class PasswordIncorrect(AppException):
    def __init__(self) -> None:
        super().__init__(status_code=400, detail="Current password is incorrect")


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _fetch_settings_or_raise(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> UserSettings:
    """Fetch user settings, raising 404 if not found."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.unique().scalar_one_or_none()
    if settings is None:
        raise SettingsNotFound()
    return settings


async def _fetch_provider_or_raise(
    db: AsyncSession,
    provider_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ApiProviderConfig:
    """Fetch an API provider config, verifying ownership."""
    result = await db.execute(
        select(ApiProviderConfig).where(
            ApiProviderConfig.id == provider_id,
            ApiProviderConfig.user_id == user_id,
        )
    )
    provider = result.unique().scalar_one_or_none()
    if provider is None:
        raise ProviderNotFound(provider_id)
    return provider


async def _fetch_session_or_raise(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> UserSession:
    """Fetch a user session, verifying ownership."""
    result = await db.execute(
        select(UserSession).where(
            UserSession.id == session_id,
            UserSession.user_id == user_id,
        )
    )
    session = result.unique().scalar_one_or_none()
    if session is None:
        raise SessionNotFound(session_id)
    return session


def _to_settings_response(s: UserSettings) -> UserSettingsResponse:
    """Convert ORM UserSettings to Pydantic response."""
    return UserSettingsResponse(
        theme=s.theme,
        timezone=s.timezone,
        language=s.language,
        default_model=s.default_model,
        default_agent_id=s.default_agent_id,
        notify_email_task_reminders=s.notify_email_task_reminders,
        notify_email_agent_completion=s.notify_email_agent_completion,
        notify_email_document_processing=s.notify_email_document_processing,
        notify_email_knowledge_indexing=s.notify_email_knowledge_indexing,
        notify_browser_task_reminders=s.notify_browser_task_reminders,
        notify_browser_agent_completion=s.notify_browser_agent_completion,
        accent_color=s.accent_color,
        sidebar_default_open=s.sidebar_default_open,
        density=s.density,
        animations_enabled=s.animations_enabled,
        font_scale=s.font_scale,
        extra_settings=s.extra_settings,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _to_provider_response(p: ApiProviderConfig) -> ApiProviderResponse:
    """Convert ORM ApiProviderConfig to Pydantic response (masks key)."""
    return ApiProviderResponse(
        id=p.id,
        provider=p.provider,
        display_name=p.display_name,
        api_key_encrypted=p.api_key_encrypted,
        config=p.config,
        is_active=p.is_active,
        order=p.order,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_session_response(s: UserSession) -> UserSessionResponse:
    """Convert ORM UserSession to Pydantic response."""
    return UserSessionResponse(
        id=s.id,
        device_name=s.device_name,
        ip_address=s.ip_address,
        user_agent=s.user_agent,
        is_current=s.is_current,
        expires_at=s.expires_at,
        revoked_at=s.revoked_at,
        created_at=s.created_at,
    )


_DEFAULT_SETTINGS: dict[str, Any] = {
    "theme": "system",
    "timezone": "UTC",
    "language": "en",
    "default_model": "gpt-4o",
    "default_agent_id": None,
    "notify_email_task_reminders": True,
    "notify_email_agent_completion": True,
    "notify_email_document_processing": True,
    "notify_email_knowledge_indexing": False,
    "notify_browser_task_reminders": True,
    "notify_browser_agent_completion": True,
    "accent_color": "indigo",
    "sidebar_default_open": True,
    "density": "comfortable",
    "animations_enabled": True,
    "font_scale": 100,
    "extra_settings": None,
}


# ── Service ────────────────────────────────────────────────────────────────────


class SettingsService:
    """User preferences, API provider configs, and session management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── User Settings ─────────────────────────────────────────────────────────

    async def get_settings(self, user_id: uuid.UUID) -> UserSettingsResponse:
        """Get user settings, auto-creating with defaults if missing."""
        try:
            settings = await _fetch_settings_or_raise(self.db, user_id)
        except SettingsNotFound:
            settings = UserSettings(user_id=user_id, **_DEFAULT_SETTINGS)
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
        return _to_settings_response(settings)

    async def update_settings(
        self,
        user_id: uuid.UUID,
        data: UserSettingsUpdate,
    ) -> UserSettingsResponse:
        """Partial update of user settings. Auto-creates if missing."""
        try:
            settings = await _fetch_settings_or_raise(self.db, user_id)
        except SettingsNotFound:
            settings = UserSettings(user_id=user_id, **_DEFAULT_SETTINGS)
            self.db.add(settings)

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(settings, field, value)

        settings.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(settings)
        return _to_settings_response(settings)

    async def reset_settings(
        self,
        user_id: uuid.UUID,
        *,
        category: str | None = None,
    ) -> UserSettingsResponse:
        """Reset settings to defaults, optionally for a specific category.

        Categories: ``general``, ``notifications``, ``appearance``, or
        ``None`` (reset all).
        """
        try:
            settings = await _fetch_settings_or_raise(self.db, user_id)
        except SettingsNotFound:
            settings = UserSettings(user_id=user_id, **_DEFAULT_SETTINGS)
            self.db.add(settings)

        if category is None or category == "all":
            for field, value in _DEFAULT_SETTINGS.items():
                setattr(settings, field, value)
        elif category == "general":
            for field in ("theme", "timezone", "language", "default_model", "default_agent_id"):
                setattr(settings, field, _DEFAULT_SETTINGS[field])
        elif category == "notifications":
            for field in (
                "notify_email_task_reminders",
                "notify_email_agent_completion",
                "notify_email_document_processing",
                "notify_email_knowledge_indexing",
                "notify_browser_task_reminders",
                "notify_browser_agent_completion",
            ):
                setattr(settings, field, _DEFAULT_SETTINGS[field])
        elif category == "appearance":
            for field in ("accent_color", "sidebar_default_open", "density", "animations_enabled", "font_scale"):
                setattr(settings, field, _DEFAULT_SETTINGS[field])
        else:
            raise ValueError(
                f"Unknown category '{category}'. Use 'general', 'notifications', "
                f"'appearance', or None for all."
            )

        settings.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(settings)
        return _to_settings_response(settings)

    # ── API Provider Config ──────────────────────────────────────────────────

    async def add_provider(
        self,
        user_id: uuid.UUID,
        data: ApiProviderCreate,
    ) -> ApiProviderResponse:
        """Add a new API provider configuration.

        Encrypts the API key before storing. Raises
        ``ProviderAlreadyExists`` if the user already has a config for
        this provider.
        """
        # Check for duplicate
        existing = await self.db.execute(
            select(ApiProviderConfig).where(
                ApiProviderConfig.user_id == user_id,
                ApiProviderConfig.provider == data.provider,
            )
        )
        if existing.unique().scalar_one_or_none() is not None:
            raise ProviderAlreadyExists(data.provider)

        # Determine next display order
        max_order = await self.db.execute(
            select(func.max(ApiProviderConfig.order)).where(
                ApiProviderConfig.user_id == user_id
            )
        )
        next_order = (max_order.scalar_one() or 0) + 1

        provider = ApiProviderConfig(
            user_id=user_id,
            provider=data.provider,
            display_name=data.display_name,
            api_key_encrypted=encrypt_api_key(data.api_key),
            config=data.config or {},
            order=next_order,
        )
        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)
        return _to_provider_response(provider)

    async def list_providers(
        self,
        user_id: uuid.UUID,
    ) -> list[ApiProviderResponse]:
        """List all API provider configs for the user, ordered by display order."""
        result = await self.db.execute(
            select(ApiProviderConfig)
            .where(ApiProviderConfig.user_id == user_id)
            .order_by(ApiProviderConfig.order)
        )
        providers = result.unique().scalars().all()
        return [_to_provider_response(p) for p in providers]

    async def update_provider(
        self,
        provider_id: uuid.UUID,
        user_id: uuid.UUID,
        data: ApiProviderUpdate,
    ) -> ApiProviderResponse:
        """Partial update of an API provider config."""
        provider = await _fetch_provider_or_raise(self.db, provider_id, user_id)

        updates = data.model_dump(exclude_unset=True)
        if "api_key" in updates and updates["api_key"] is not None:
            updates["api_key_encrypted"] = encrypt_api_key(updates.pop("api_key"))

        for field, value in updates.items():
            setattr(provider, field, value)

        await self.db.commit()
        await self.db.refresh(provider)
        return _to_provider_response(provider)

    async def remove_provider(
        self,
        provider_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete an API provider configuration."""
        provider = await _fetch_provider_or_raise(self.db, provider_id, user_id)
        await self.db.delete(provider)
        await self.db.commit()

    async def validate_provider_key(
        self,
        provider_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Validate an API key by decrypting and testing connectivity.

        Returns a dict with ``valid`` (bool) and optional ``error`` message.
        This is a placeholder — actual provider-specific validation will
        be added per-provider in a future milestone.
        """
        provider = await _fetch_provider_or_raise(self.db, provider_id, user_id)

        try:
            decrypted = decrypt_api_key(provider.api_key_encrypted)
        except Exception:
            return {"valid": False, "error": "Failed to decrypt API key"}

        if not decrypted or len(decrypted) < 8:
            return {"valid": False, "error": "Decrypted key appears invalid"}

        # TODO: provider-specific connectivity check per provider type
        return {"valid": True, "provider": provider.provider}

    # ── User Sessions ─────────────────────────────────────────────────────────

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        *,
        current_jti: str | None = None,
    ) -> list[UserSessionResponse]:
        """List all active (non-revoked) sessions for the user.

        If ``current_jti`` is provided, marks the matching session as current.
        """
        result = await self.db.execute(
            select(UserSession)
            .where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
            .order_by(UserSession.created_at.desc())
        )
        sessions = result.unique().scalars().all()

        responses = []
        for s in sessions:
            resp = _to_session_response(s)
            if current_jti and s.jti == current_jti:
                resp.is_current = True
            responses.append(resp)
        return responses

    async def revoke_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Revoke a specific session by ID."""
        session = await _fetch_session_or_raise(self.db, session_id, user_id)
        if session.revoked_at is not None:
            # Already revoked — idempotent
            return
        session.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def revoke_all_other_sessions(
        self,
        user_id: uuid.UUID,
        current_jti: str,
    ) -> int:
        """Revoke all sessions except the one matching *current_jti*.

        Returns the number of revoked sessions.
        """
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.user_id == user_id,
                UserSession.jti != current_jti,
                UserSession.revoked_at.is_(None),
            )
        )
        sessions = result.unique().scalars().all()
        now = datetime.now(timezone.utc)
        for s in sessions:
            s.revoked_at = now
        await self.db.commit()
        return len(sessions)

    # ── Password Change ───────────────────────────────────────────────────────

    async def change_password(
        self,
        user_id: uuid.UUID,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change the user's password after verifying the current one."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.unique().scalar_one_or_none()
        if user is None:
            raise AppException(status_code=404, detail="User not found")

        if not verify_password(current_password, user.hashed_password):
            raise PasswordIncorrect()

        user.hashed_password = hash_password(new_password)
        await self.db.commit()

    # ── Import / Export ───────────────────────────────────────────────────────

    async def export_settings(
        self,
        user_id: uuid.UUID,
        current_jti: str | None = None,
    ) -> SettingsExportResponse:
        """Export all settings, provider configs, and session count."""
        settings = await self.get_settings(user_id)
        providers = await self.list_providers(user_id)

        # Count active sessions
        result = await self.db.execute(
            select(func.count()).where(
                UserSession.user_id == user_id,
                UserSession.revoked_at.is_(None),
            )
        )
        session_count = result.scalar_one()

        return SettingsExportResponse(
            settings=settings,
            providers=providers,
            session_count=session_count,
        )

    async def import_settings(
        self,
        user_id: uuid.UUID,
        data: SettingsImport,
    ) -> UserSettingsResponse:
        """Import settings and optionally provider configs.

        Only the ``settings`` and ``providers`` sections are imported.
        Sessions are never imported.
        """
        settings_response = await self.update_settings(user_id, data.settings)

        # Import providers (add missing, skip duplicates)
        for provider_data in data.providers:
            existing = await self.db.execute(
                select(ApiProviderConfig).where(
                    ApiProviderConfig.user_id == user_id,
                    ApiProviderConfig.provider == provider_data.provider,
                )
            )
            if existing.unique().scalar_one_or_none() is None:
                await self.add_provider(user_id, provider_data)

        return settings_response
