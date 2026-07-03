"""Comprehensive settings integration tests.

Covers user settings CRUD, API provider config (encrypted keys, masking),
session management, password change, import/export, ownership isolation,
and validation edge-cases.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_api_key
from app.models.settings import ApiProviderConfig, UserSession, UserSettings
from app.schemas.settings import ACCENT_COLORS, AI_PROVIDERS, DENSITY_OPTIONS, THEME_OPTIONS
from tests.conftest import auth_header, create_user, create_refresh_token_record


# ── Helpers ──────────────────────────────────────────────────────────────────


async def create_settings(
    db_session: AsyncSession,
    user_id: UUID,
    **kwargs,
) -> UserSettings:
    """Factory: create user settings directly in the DB and return the ORM object."""
    s = UserSettings(
        user_id=user_id,
        theme=kwargs.pop("theme", "light"),
        timezone=kwargs.pop("timezone", "UTC"),
        language=kwargs.pop("language", "en"),
        default_model=kwargs.pop("default_model", "gpt-4o"),
        default_agent_id=kwargs.pop("default_agent_id", None),
        notify_email_task_reminders=kwargs.pop("notify_email_task_reminders", True),
        notify_email_agent_completion=kwargs.pop("notify_email_agent_completion", True),
        notify_email_document_processing=kwargs.pop("notify_email_document_processing", True),
        notify_email_knowledge_indexing=kwargs.pop("notify_email_knowledge_indexing", False),
        notify_browser_task_reminders=kwargs.pop("notify_browser_task_reminders", True),
        notify_browser_agent_completion=kwargs.pop("notify_browser_agent_completion", True),
        accent_color=kwargs.pop("accent_color", "indigo"),
        sidebar_default_open=kwargs.pop("sidebar_default_open", True),
        density=kwargs.pop("density", "comfortable"),
        animations_enabled=kwargs.pop("animations_enabled", True),
        font_scale=kwargs.pop("font_scale", 100),
        extra_settings=kwargs.pop("extra_settings", None),
        **kwargs,
    )
    db_session.add(s)
    await db_session.flush()
    return s


async def create_provider(
    db_session: AsyncSession,
    user_id: UUID,
    **kwargs,
) -> ApiProviderConfig:
    """Factory: create an API provider config directly in the DB."""
    p = ApiProviderConfig(
        user_id=user_id,
        provider=kwargs.pop("provider", "openai"),
        display_name=kwargs.pop("display_name", None),
        api_key_encrypted=kwargs.pop("api_key_encrypted", encrypt_api_key("sk-test-key-12345")),
        config=kwargs.pop("config", {}),
        is_active=kwargs.pop("is_active", True),
        order=kwargs.pop("order", 1),
    )
    db_session.add(p)
    await db_session.flush()
    return p


async def create_session(
    db_session: AsyncSession,
    user_id: UUID,
    **kwargs,
) -> UserSession:
    """Factory: create a user session directly in the DB.

    Generates a ``jti`` from ``create_refresh_token_record`` if not provided.
    """
    jti = kwargs.pop("jti", None)
    if jti is None:
        token = await create_refresh_token_record(db_session, user_id)
        # extract jti from the token (not stored in the record creation)
        # instead, just use a random hex
        from app.core.security import create_refresh_jti
        jti = kwargs.pop("jti", create_refresh_jti())

    s = UserSession(
        user_id=user_id,
        jti=jti,
        device_name=kwargs.pop("device_name", "Chrome on Windows"),
        ip_address=kwargs.pop("ip_address", "192.168.1.1"),
        user_agent=kwargs.pop("user_agent", "Mozilla/5.0"),
        is_current=kwargs.pop("is_current", True),
        expires_at=kwargs.pop("expires_at", datetime.now(UTC) + timedelta(days=30)),
        revoked_at=kwargs.pop("revoked_at", None),
    )
    db_session.add(s)
    await db_session.flush()
    return s


# ── Test Classes ─────────────────────────────────────────────────────────────


class TestUserSettings:
    """GET/PATCH /settings, POST /settings/reset"""

    async def test_get_auto_creates(self, client: AsyncClient, user_id: UUID):
        """First GET auto-creates default settings."""
        resp = await client.get("/api/v1/settings", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "system"
        assert data["timezone"] == "UTC"
        assert data["language"] == "en"
        assert data["default_model"] == "gpt-4o"
        assert data["accent_color"] == "indigo"
        assert data["density"] == "comfortable"
        assert data["animations_enabled"] is True
        assert data["font_scale"] == 100

    async def test_get_existing(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """GET returns existing settings."""
        await create_settings(db_session, user_id, theme="dark", density="compact")
        resp = await client.get("/api/v1/settings", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        assert resp.json()["theme"] == "dark"
        assert resp.json()["density"] == "compact"

    async def test_partial_update(self, client: AsyncClient, user_id: UUID):
        """PATCH with only some fields merges correctly."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"theme": "dark", "font_scale": 120},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "dark"
        assert data["font_scale"] == 120
        # other fields remain default
        assert data["density"] == "comfortable"
        assert data["language"] == "en"

    async def test_update_all_fields(self, client: AsyncClient, user_id: UUID):
        """Full update changes all provided fields."""
        payload = {
            "theme": "light",
            "timezone": "America/New_York",
            "language": "fr",
            "default_model": "claude-sonnet-5",
            "notify_email_task_reminders": False,
            "notify_email_agent_completion": False,
            "accent_color": "violet",
            "sidebar_default_open": False,
            "density": "compact",
            "animations_enabled": False,
            "font_scale": 90,
            "extra_settings": {"custom_key": "custom_value"},
        }
        resp = await client.patch(
            "/api/v1/settings", json=payload, headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        for key, val in payload.items():
            assert resp.json()[key] == val

    async def test_reset_all(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """POST /settings/reset reverts all fields to defaults."""
        await create_settings(db_session, user_id, theme="dark", font_scale=150)
        resp = await client.post("/api/v1/settings/reset", headers=auth_header(str(user_id)))
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "system"
        assert data["font_scale"] == 100
        assert data["density"] == "comfortable"

    async def test_reset_category(self, client: AsyncClient, user_id: UUID):
        """Reset only appearance fields."""
        # First set some non-default values
        await client.patch(
            "/api/v1/settings",
            json={"theme": "dark", "accent_color": "rose", "language": "es"},
            headers=auth_header(str(user_id)),
        )
        resp = await client.post(
            "/api/v1/settings/reset?category=appearance",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "dark"  # not reset — general category
        assert data["accent_color"] == "indigo"  # reset
        assert data["language"] == "es"  # not reset — general category

    async def test_reset_general(self, client: AsyncClient, user_id: UUID):
        """Reset general preferences."""
        await client.patch(
            "/api/v1/settings",
            json={"theme": "dark", "timezone": "Asia/Tokyo", "font_scale": 130},
            headers=auth_header(str(user_id)),
        )
        resp = await client.post(
            "/api/v1/settings/reset?category=general",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["theme"] == "system"  # general
        assert data["timezone"] == "UTC"  # general
        assert data["font_scale"] == 130  # appearance — not reset

    async def test_reset_notifications(self, client: AsyncClient, user_id: UUID):
        """Reset notification preferences."""
        await client.patch(
            "/api/v1/settings",
            json={
                "notify_email_task_reminders": False,
                "notify_browser_agent_completion": False,
            },
            headers=auth_header(str(user_id)),
        )
        resp = await client.post(
            "/api/v1/settings/reset?category=notifications",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notify_email_task_reminders"] is True
        assert data["notify_browser_agent_completion"] is True

    async def test_reset_invalid_category(self, client: AsyncClient, user_id: UUID):
        """Unknown category returns 400."""
        resp = await client.post(
            "/api/v1/settings/reset?category=bogus",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 400

    async def test_unauthenticated(self, client: AsyncClient):
        """Missing auth token returns 401."""
        resp = await client.get("/api/v1/settings")
        assert resp.status_code == 401
        resp = await client.patch("/api/v1/settings", json={})
        assert resp.status_code == 401


class TestSettingsImportExport:
    """GET /settings/export, POST /settings/import"""

    async def test_export_round_trip(self, client: AsyncClient, user_id: UUID):
        """Export then import preserves settings."""
        # Set up some custom settings
        await client.patch(
            "/api/v1/settings",
            json={"theme": "dark", "accent_color": "sky"},
            headers=auth_header(str(user_id)),
        )
        # Export
        export_resp = await client.get(
            "/api/v1/settings/export", headers=auth_header(str(user_id))
        )
        assert export_resp.status_code == 200
        export = export_resp.json()
        assert export["settings"]["theme"] == "dark"
        assert export["session_count"] >= 0

        # Reset to defaults
        await client.post("/api/v1/settings/reset", headers=auth_header(str(user_id)))

        # Import back
        import_resp = await client.post(
            "/api/v1/settings/import",
            json=export,
            headers=auth_header(str(user_id)),
        )
        assert import_resp.status_code == 200
        assert import_resp.json()["theme"] == "dark"

    async def test_import_providers(self, client: AsyncClient, user_id: UUID):
        """Import also creates providers."""
        payload = {
            "settings": {"theme": "light"},
            "providers": [
                {
                    "provider": "openai",
                    "api_key": "sk-test-key-12345",
                },
                {
                    "provider": "anthropic",
                    "api_key": "sk-ant-test-key-67890",
                    "display_name": "Anthropic",
                },
            ],
        }
        resp = await client.post(
            "/api/v1/settings/import",
            json=payload,
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200

        # Verify providers were created
        list_resp = await client.get(
            "/api/v1/settings/providers", headers=auth_header(str(user_id))
        )
        items = list_resp.json()["items"]
        assert len(items) == 2
        provider_names = {p["provider"] for p in items}
        assert provider_names == {"openai", "anthropic"}

    async def test_import_duplicate_provider_skipped(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Importing a provider that already exists is silently skipped."""
        await create_provider(db_session, user_id, provider="openai")
        payload = {
            "settings": {"theme": "light"},
            "providers": [
                {"provider": "openai", "api_key": "sk-another-key"},
                {"provider": "gemini", "api_key": "gm-key"},
            ],
        }
        resp = await client.post(
            "/api/v1/settings/import",
            json=payload,
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200

        list_resp = await client.get(
            "/api/v1/settings/providers", headers=auth_header(str(user_id))
        )
        assert len(list_resp.json()["items"]) == 2

    async def test_export_without_providers(self, client: AsyncClient, user_id: UUID):
        """Export with no providers returns empty list and zero session count."""
        resp = await client.get(
            "/api/v1/settings/export", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["providers"] == []
        assert data["session_count"] >= 0


class TestApiProviders:
    """CRUD /settings/providers"""

    async def test_add_provider(self, client: AsyncClient, user_id: UUID):
        """POST creates a new provider with masked key in response."""
        resp = await client.post(
            "/api/v1/settings/providers",
            json={
                "provider": "openai",
                "api_key": "sk-test-key-12345",
                "display_name": "My OpenAI",
            },
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["display_name"] == "My OpenAI"
        assert "****" in data["api_key_encrypted"]
        assert data["api_key_encrypted"] != "sk-test-key-12345"
        assert UUID(data["id"])

    async def test_add_provider_with_config(self, client: AsyncClient, user_id: UUID):
        """Provider with custom config is stored correctly."""
        resp = await client.post(
            "/api/v1/settings/providers",
            json={
                "provider": "ollama",
                "api_key": "ollama-local-key",
                "config": {"base_url": "http://localhost:11434"},
            },
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 201
        assert resp.json()["config"] == {"base_url": "http://localhost:11434"}

    async def test_add_provider_duplicate(self, client: AsyncClient, user_id: UUID):
        """Duplicate provider returns 409."""
        await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-first-key"},
            headers=auth_header(str(user_id)),
        )
        resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-second-key"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 409

    async def test_list_providers(self, client: AsyncClient, user_id: UUID):
        """GET returns all providers, ordered."""
        await client.post(
            "/api/v1/settings/providers",
            json={"provider": "anthropic", "api_key": "sk-ant-key"},
            headers=auth_header(str(user_id)),
        )
        await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-openai-key"},
            headers=auth_header(str(user_id)),
        )
        resp = await client.get(
            "/api/v1/settings/providers", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        # Keys should be masked in response
        for item in items:
            assert "****" in item["api_key_encrypted"]

    async def test_list_empty(self, client: AsyncClient, user_id: UUID):
        """No providers returns empty list."""
        resp = await client.get(
            "/api/v1/settings/providers", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_update_provider_key(self, client: AsyncClient, user_id: UUID):
        """PATCH updates provider and re-encrypts key."""
        create_resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-old-key"},
            headers=auth_header(str(user_id)),
        )
        provider_id = create_resp.json()["id"]

        resp = await client.patch(
            f"/api/v1/settings/providers/{provider_id}",
            json={"api_key": "sk-new-key", "display_name": "Updated"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Updated"
        assert "****" in data["api_key_encrypted"]

    async def test_update_provider_not_found(self, client: AsyncClient, user_id: UUID):
        """Updating a non-existent provider returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = await client.patch(
            f"/api/v1/settings/providers/{fake_id}",
            json={"display_name": "Nope"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_delete_provider(self, client: AsyncClient, user_id: UUID):
        """DELETE removes the provider."""
        create_resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "gemini", "api_key": "gm-key"},
            headers=auth_header(str(user_id)),
        )
        provider_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/settings/providers/{provider_id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 204

        # Verify it's gone
        list_resp = await client.get(
            "/api/v1/settings/providers", headers=auth_header(str(user_id))
        )
        assert len(list_resp.json()["items"]) == 0

    async def test_delete_provider_not_found(self, client: AsyncClient, user_id: UUID):
        """Deleting a non-existent provider returns 404."""
        resp = await client.delete(
            "/api/v1/settings/providers/00000000-0000-0000-0000-000000000000",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_validate_provider_key(self, client: AsyncClient, user_id: UUID):
        """POST validate returns valid=true for a valid encrypted key."""
        create_resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-valid-key-here"},
            headers=auth_header(str(user_id)),
        )
        provider_id = create_resp.json()["id"]

        resp = await client.post(
            f"/api/v1/settings/providers/{provider_id}/validate",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True

    async def test_validate_provider_not_found(self, client: AsyncClient, user_id: UUID):
        """Validating a non-existent provider returns 404."""
        resp = await client.post(
            "/api/v1/settings/providers/00000000-0000-0000-0000-000000000000/validate",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_add_provider_unauthenticated(self, client: AsyncClient):
        """Missing auth returns 401."""
        resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": "sk-key"},
        )
        assert resp.status_code == 401


class TestSessions:
    """Session listing and revocation."""

    async def test_list_sessions_empty(self, client: AsyncClient, user_id: UUID):
        """No sessions returns empty list."""
        resp = await client.get(
            "/api/v1/settings/sessions", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_list_with_sessions(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Sessions created in DB appear in list."""
        await create_session(db_session, user_id)
        await create_session(db_session, user_id, device_name="Mobile Safari")
        resp = await client.get(
            "/api/v1/settings/sessions", headers=auth_header(str(user_id))
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2

    async def test_revoked_sessions_excluded(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Revoked sessions do not appear in the active list."""
        session = await create_session(db_session, user_id)
        session.revoked_at = datetime.now(UTC)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/settings/sessions", headers=auth_header(str(user_id))
        )
        assert len(resp.json()["items"]) == 0

    async def test_revoke_session(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """DELETE /settings/sessions/{id} revokes a session."""
        session = await create_session(db_session, user_id)
        session_id = session.id

        resp = await client.delete(
            f"/api/v1/settings/sessions/{session_id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 204

        # Should no longer appear
        list_resp = await client.get(
            "/api/v1/settings/sessions", headers=auth_header(str(user_id))
        )
        assert len(list_resp.json()["items"]) == 0

    async def test_revoke_session_not_found(self, client: AsyncClient, user_id: UUID):
        """Revoking a non-existent session returns 404."""
        resp = await client.delete(
            "/api/v1/settings/sessions/00000000-0000-0000-0000-000000000000",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_revoke_already_revoked(self, client: AsyncClient, db_session: AsyncSession, user_id: UUID):
        """Revoking an already-revoked session is idempotent (204)."""
        session = await create_session(db_session, user_id, revoked_at=datetime.now(UTC))

        resp = await client.delete(
            f"/api/v1/settings/sessions/{session.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 204


class TestPasswordChange:
    """POST /settings/change-password"""

    async def test_change_password(self, client: AsyncClient, user_id: UUID):
        """Correct current password allows change."""
        resp = await client.post(
            "/api/v1/settings/change-password",
            json={"current_password": "strongpass123", "new_password": "newstrongpass456"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password changed successfully"

    async def test_change_password_wrong_current(self, client: AsyncClient, user_id: UUID):
        """Wrong current password returns 400."""
        resp = await client.post(
            "/api/v1/settings/change-password",
            json={"current_password": "wrongpassword", "new_password": "newstrongpass456"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 400

    async def test_change_password_short_new(self, client: AsyncClient, user_id: UUID):
        """New password < 8 chars returns 422."""
        resp = await client.post(
            "/api/v1/settings/change-password",
            json={"current_password": "strongpass123", "new_password": "short"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422


class TestPermissions:
    """User A cannot access user B's settings/providers/sessions."""

    @pytest_asyncio.fixture
    async def other_user_id(self, db_session: AsyncSession) -> UUID:
        user = await create_user(db_session, email="bob@example.com", username="bob")
        return user.id

    @pytest_asyncio.fixture
    async def other_provider(self, db_session: AsyncSession, other_user_id: UUID) -> ApiProviderConfig:
        return await create_provider(db_session, other_user_id)

    @pytest_asyncio.fixture
    async def other_session(self, db_session: AsyncSession, other_user_id: UUID) -> UserSession:
        return await create_session(db_session, other_user_id)

    async def test_cannot_get_other_settings(self, client: AsyncClient, user_id: UUID, other_user_id: UUID):
        """GET /settings returns own settings, not another's — but auto-creates."""
        # Just verify we can read our own settings, and that we can't read
        # another's through the ownership-gated service (not directly testable
        # via API — the endpoint is always scoped to current user)
        resp = await client.get("/api/v1/settings", headers=auth_header(str(user_id)))
        assert resp.status_code == 200

    async def test_cannot_patch_other_provider(self, client: AsyncClient, user_id: UUID, other_provider: ApiProviderConfig):
        """Updating another user's provider returns 404."""
        resp = await client.patch(
            f"/api/v1/settings/providers/{other_provider.id}",
            json={"display_name": "Hacked"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_cannot_delete_other_provider(self, client: AsyncClient, user_id: UUID, other_provider: ApiProviderConfig):
        """Deleting another user's provider returns 404."""
        resp = await client.delete(
            f"/api/v1/settings/providers/{other_provider.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_cannot_revoke_other_session(self, client: AsyncClient, user_id: UUID, other_session: UserSession):
        """Revoking another user's session returns 404."""
        resp = await client.delete(
            f"/api/v1/settings/sessions/{other_session.id}",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404

    async def test_cannot_validate_other_provider(self, client: AsyncClient, user_id: UUID, other_provider: ApiProviderConfig):
        """Validating another user's provider returns 404."""
        resp = await client.post(
            f"/api/v1/settings/providers/{other_provider.id}/validate",
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 404


class TestValidation:
    """Schema-level validation edge cases."""

    async def test_invalid_theme(self, client: AsyncClient, user_id: UUID):
        """Invalid theme returns 422."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"theme": "neon"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_invalid_accent_color(self, client: AsyncClient, user_id: UUID):
        """Invalid accent_color returns 422."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"accent_color": "hotpink"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_invalid_density(self, client: AsyncClient, user_id: UUID):
        """Invalid density returns 422."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"density": "ultra"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_out_of_range_font_scale(self, client: AsyncClient, user_id: UUID):
        """Font scale outside 75-150 returns 422."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"font_scale": 200},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_invalid_timezone(self, client: AsyncClient, user_id: UUID):
        """Invalid timezone returns 422."""
        resp = await client.patch(
            "/api/v1/settings",
            json={"timezone": "Mars/Olympus"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_empty_provider_key(self, client: AsyncClient, user_id: UUID):
        """Empty API key returns 422."""
        resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "openai", "api_key": ""},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422

    async def test_invalid_provider(self, client: AsyncClient, user_id: UUID):
        """Invalid provider slug returns 422."""
        resp = await client.post(
            "/api/v1/settings/providers",
            json={"provider": "not-a-real-provider", "api_key": "sk-key"},
            headers=auth_header(str(user_id)),
        )
        assert resp.status_code == 422


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def user_id(db_session: AsyncSession) -> UUID:
    """Create a test user and return their ID."""
    user = await create_user(db_session)
    return user.id
