"""Settings, API provider, and session ORM models.

``UserSettings`` stores user preferences in strongly typed columns —
no JSONB blobs for common settings.  ``ApiProviderConfig`` stores
encrypted API keys.  ``UserSession`` tracks active login sessions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


# ── User Settings ────────────────────────────────────────────────────────────


class UserSettings(UUIDMixin, TimestampMixin, Base):
    """User preferences and workspace configuration.

    All common settings live in strongly typed columns.  The
    ``extra_settings`` JSONB column exists only for future/custom
    settings that don't warrant a new typed column yet.
    """

    __tablename__ = "user_settings"

    # ── Ownership ─────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="FK to users.id (one-to-one)",
    )

    # ── General preferences ───────────────────────────────────────
    theme: Mapped[str] = mapped_column(
        String(20),
        default="system",
        nullable=False,
        comment='Theme: "light", "dark", or "system"',
    )
    timezone: Mapped[str] = mapped_column(
        String(50),
        default="UTC",
        nullable=False,
        comment="IANA timezone identifier (e.g. America/New_York)",
    )
    language: Mapped[str] = mapped_column(
        String(10),
        default="en",
        nullable=False,
        comment="Locale / language code (e.g. en, es, fr)",
    )
    default_model: Mapped[str] = mapped_column(
        String(100),
        default="gpt-4o",
        nullable=False,
        comment="Default AI model for new agents and chat sessions",
    )
    default_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        nullable=True,
        comment="Default agent to load on the agents page",
    )

    # ── Notification preferences ──────────────────────────────────
    notify_email_task_reminders: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notify_email_agent_completion: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notify_email_document_processing: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notify_email_knowledge_indexing: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    notify_browser_task_reminders: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    notify_browser_agent_completion: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    # ── Appearance settings ───────────────────────────────────────
    accent_color: Mapped[str] = mapped_column(
        String(20),
        default="indigo",
        nullable=False,
        comment="Accent color: indigo, emerald, amber, rose, violet, sky",
    )
    sidebar_default_open: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    density: Mapped[str] = mapped_column(
        String(20),
        default="comfortable",
        nullable=False,
        comment='UI density: "comfortable" or "compact"',
    )
    animations_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    font_scale: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
        comment="Font size scale percentage (75–150)",
    )

    # ── Extensible JSONB for future/custom settings ──────────────
    extra_settings: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        nullable=True,
        comment="Future/custom settings not yet covered by typed columns",
    )

    # ── Relationship ──────────────────────────────────────────────
    user = relationship("User", back_populates="settings")


# ── API Provider Config ─────────────────────────────────────────────────────


class ApiProviderConfig(UUIDMixin, TimestampMixin, Base):
    """Encrypted API key store for external AI providers.

    The ``api_key_encrypted`` field contains a Fernet-encrypted key.
    The plaintext key is never exposed via the API — only masked
    representations are returned to the frontend.
    """

    __tablename__ = "api_provider_configs"

    # ── Ownership ─────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users.id",
    )

    # ── Provider identity ─────────────────────────────────────────
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Provider slug: openai, anthropic, gemini, openrouter, groq, azure_openai, ollama",
    )
    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional human-readable label",
    )

    # ── Credentials (encrypted) ───────────────────────────────────
    api_key_encrypted: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Fernet-encrypted API key — never decrypted in API responses",
    )

    # ── Provider-specific config ──────────────────────────────────
    config: Mapped[dict | None] = mapped_column(
        JSONB,
        default=dict,
        nullable=True,
        comment="Provider-specific config: base_url, org_id, azure_endpoint, etc.",
    )

    # ── State ─────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    order: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Display order (lower = first)"
    )

    # ── Constraints ──────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint(
            "user_id", "provider", name="uq_user_provider"
        ),
    )

    # ── Relationship ──────────────────────────────────────────────
    user = relationship("User", back_populates="api_provider_configs")


# ── User Session ────────────────────────────────────────────────────────────


class UserSession(UUIDMixin, TimestampMixin, Base):
    """Active user session for security settings display.

    Sessions are created alongside refresh tokens.  Users can view
    and revoke their sessions from the Security settings page.
    """

    __tablename__ = "user_sessions"

    # ── Ownership ─────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK to users.id",
    )

    # ── Session identity ──────────────────────────────────────────
    jti: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="JWT ID — links this session to a refresh token",
    )

    # ── Client info ───────────────────────────────────────────────
    device_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User-facing device label",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="Client IP address (IPv4 or IPv6)",
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Raw User-Agent header",
    )

    # ── State ─────────────────────────────────────────────────────
    is_current: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of manual revocation",
    )

    # ── Relationship ──────────────────────────────────────────────
    user = relationship("User", back_populates="sessions")
