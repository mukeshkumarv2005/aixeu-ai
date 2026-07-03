"""Pydantic schemas for the Settings & Workspace Configuration system.

Covers user settings, API provider config, user sessions, and
settings import/export.  All schemas use ``from_attributes = True``
for ORM compatibility.

    AI Providers:   openai, anthropic, gemini, openrouter, groq,
                    azure_openai, ollama
    Accent colors:  indigo, emerald, amber, rose, violet, sky
    Themes:         light, dark, system
    Density:        comfortable, compact
"""

from __future__ import annotations

import zoneinfo
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Constants ────────────────────────────────────────────────────────────────

AI_PROVIDERS = frozenset({
    "openai", "anthropic", "gemini", "openrouter", "groq",
    "azure_openai", "ollama",
})

ACCENT_COLORS = frozenset({
    "indigo", "emerald", "amber", "rose", "violet", "sky",
})

THEME_OPTIONS = frozenset({"light", "dark", "system"})

DENSITY_OPTIONS = frozenset({"comfortable", "compact"})

FONT_SCALE_RANGE = range(75, 151)  # 75–150 inclusive


# ── Helpers ──────────────────────────────────────────────────────────────────


def _mask_api_key(key: str) -> str:
    """Return sk-****abcd — first 3 + last 4 chars."""
    if len(key) <= 7:
        return "****"
    return key[:3] + "****" + key[-4:]


# ── User Settings ───────────────────────────────────────────────────────────


class UserSettingsResponse(BaseModel):
    """Full user settings read response.

    All common settings are strongly typed columns.  ``extra_settings``
    JSONB is available for future/custom settings.
    """

    # General preferences
    theme: str = "system"
    timezone: str = "UTC"
    language: str = "en"
    default_model: str = "gpt-4o"
    default_agent_id: UUID | None = None

    # Notification preferences
    notify_email_task_reminders: bool = True
    notify_email_agent_completion: bool = True
    notify_email_document_processing: bool = True
    notify_email_knowledge_indexing: bool = False
    notify_browser_task_reminders: bool = True
    notify_browser_agent_completion: bool = True

    # Appearance settings
    accent_color: str = "indigo"
    sidebar_default_open: bool = True
    density: str = "comfortable"
    animations_enabled: bool = True
    font_scale: int = 100

    # Extensible JSONB
    extra_settings: dict | None = None

    # Timestamps
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        v = v.lower()
        if v not in THEME_OPTIONS:
            raise ValueError(
                f"Invalid theme '{v}'. Must be one of: {', '.join(sorted(THEME_OPTIONS))}"
            )
        return v

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, v: str) -> str:
        v = v.lower()
        if v not in ACCENT_COLORS:
            raise ValueError(
                f"Invalid accent_color '{v}'. Must be one of: {', '.join(sorted(ACCENT_COLORS))}"
            )
        return v

    @field_validator("density")
    @classmethod
    def validate_density(cls, v: str) -> str:
        v = v.lower()
        if v not in DENSITY_OPTIONS:
            raise ValueError(
                f"Invalid density '{v}'. Must be one of: {', '.join(sorted(DENSITY_OPTIONS))}"
            )
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone key by attempting to load it via ZoneInfo."""
        try:
            zoneinfo.ZoneInfo(v)
        except (KeyError, zoneinfo.ZoneInfoNotFoundError):
            raise ValueError(f"Unknown timezone '{v}'") from None
        return v

    @field_validator("font_scale")
    @classmethod
    def validate_font_scale(cls, v: int) -> int:
        if v < 75 or v > 150:
            raise ValueError(f"font_scale must be between 75 and 150 (got {v})")
        return v


class UserSettingsUpdate(BaseModel):
    """Request to update user settings (partial update).

    All fields are optional; only provided fields are changed.
    """

    theme: str | None = None
    timezone: str | None = None
    language: str | None = None
    default_model: str | None = None
    default_agent_id: UUID | None = None

    notify_email_task_reminders: bool | None = None
    notify_email_agent_completion: bool | None = None
    notify_email_document_processing: bool | None = None
    notify_email_knowledge_indexing: bool | None = None
    notify_browser_task_reminders: bool | None = None
    notify_browser_agent_completion: bool | None = None

    accent_color: str | None = None
    sidebar_default_open: bool | None = None
    density: str | None = None
    animations_enabled: bool | None = None
    font_scale: int | None = None

    extra_settings: dict | None = None

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if v is None:
            return v
        v = v.lower()
        if v not in THEME_OPTIONS:
            raise ValueError(
                f"Invalid theme '{v}'. Must be one of: {', '.join(sorted(THEME_OPTIONS))}"
            )
        return v

    @field_validator("accent_color")
    @classmethod
    def validate_accent_color(cls, v: str) -> str:
        if v is None:
            return v
        v = v.lower()
        if v not in ACCENT_COLORS:
            raise ValueError(
                f"Invalid accent_color '{v}'. Must be one of: {', '.join(sorted(ACCENT_COLORS))}"
            )
        return v

    @field_validator("density")
    @classmethod
    def validate_density(cls, v: str) -> str:
        if v is None:
            return v
        v = v.lower()
        if v not in DENSITY_OPTIONS:
            raise ValueError(
                f"Invalid density '{v}'. Must be one of: {', '.join(sorted(DENSITY_OPTIONS))}"
            )
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            zoneinfo.ZoneInfo(v)
        except (KeyError, zoneinfo.ZoneInfoNotFoundError):
            raise ValueError(f"Unknown timezone '{v}'") from None
        return v

    @field_validator("font_scale")
    @classmethod
    def validate_font_scale(cls, v: int) -> int:
        if v is None:
            return v
        if v < 75 or v > 150:
            raise ValueError(f"font_scale must be between 75 and 150 (got {v})")
        return v


# ── API Provider Config ─────────────────────────────────────────────────────


class ApiProviderCreate(BaseModel):
    """Request to add a new API provider configuration."""

    provider: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Provider slug",
    )
    display_name: str | None = Field(
        None,
        max_length=255,
        description="Optional human-readable label",
    )
    api_key: str = Field(
        ...,
        min_length=1,
        description="API key (will be encrypted at rest)",
    )
    config: dict | None = Field(
        None,
        description="Provider-specific config: base_url, org_id, azure_endpoint, etc.",
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        v = v.lower()
        if v not in AI_PROVIDERS:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(sorted(AI_PROVIDERS))}"
            )
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("API key must not be empty")
        return v


class ApiProviderUpdate(BaseModel):
    """Request to update an API provider configuration (partial update)."""

    display_name: str | None = None
    api_key: str | None = Field(
        None, description="New API key (will be re-encrypted at rest)"
    )
    config: dict | None = None
    is_active: bool | None = None

    @field_validator("api_key")
    @classmethod
    def validate_api_key_format(cls, v: str) -> str:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("API key must not be empty")
        return v


class ApiProviderResponse(BaseModel):
    """Full API provider config read response.

    The ``api_key_encrypted`` field is automatically masked in the
    response — only the first 3 and last 4 characters are visible.
    """

    id: UUID
    provider: str
    display_name: str | None = None
    api_key_encrypted: str = Field(
        ..., description="Masked API key (sk-****abcd)"
    )
    config: dict | None = None
    is_active: bool = True
    order: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("api_key_encrypted", mode="before")
    @classmethod
    def mask_key_in_response(cls, v: str) -> str:
        """Mask the encrypted key so the raw ciphertext is never exposed."""
        if v and not v.startswith("****"):
            return _mask_api_key(v)
        return v


class ApiProviderListResponse(BaseModel):
    """List of configured API providers."""

    items: list[ApiProviderResponse] = Field(default_factory=list)


# ── User Session ────────────────────────────────────────────────────────────


class UserSessionResponse(BaseModel):
    """Full user session read response.

    The ``jti`` field is intentionally excluded — the session ID in the
    URL serves as the identifier for revocation.
    """

    id: UUID
    device_name: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    is_current: bool = False
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSessionListResponse(BaseModel):
    """List of active user sessions."""

    items: list[UserSessionResponse] = Field(default_factory=list)


# ── Password Change ─────────────────────────────────────────────────────────


class PasswordChangeRequest(BaseModel):
    """Request to change the user's password."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 characters)",
    )


# ── Settings Import / Export ────────────────────────────────────────────────


class SettingsExportResponse(BaseModel):
    """Full settings export including providers with masked keys."""

    settings: UserSettingsResponse
    providers: list[ApiProviderResponse] = Field(default_factory=list)
    session_count: int = Field(default=0, description="Number of active sessions")


class SettingsImport(BaseModel):
    """Import payload — mirrors export shape.

    Only the ``settings`` and ``providers`` sections are imported.
    Sessions are never imported.
    """

    settings: UserSettingsUpdate
    providers: list[ApiProviderCreate] = Field(
        default_factory=list,
        description="Provider configs to import (API keys required)",
    )
