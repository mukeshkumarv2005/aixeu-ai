"""Add Settings & Workspace Configuration tables.

Creates ``user_settings``, ``api_provider_configs``, and
``user_sessions`` tables, and adds ``last_login_at`` and
``two_factor_enabled`` columns to ``users``.

Revision ID: 010
Revises: 009
Create Date: 2026-07-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── user_settings ────────────────────────────────────────────────────────────
    op.create_table(
        "user_settings",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership (one-to-one)
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            comment="FK to users.id (one-to-one)",
        ),
        # General preferences
        sa.Column(
            "theme",
            sa.String(20),
            nullable=False,
            server_default="system",
            comment='Theme: "light", "dark", or "system"',
        ),
        sa.Column(
            "timezone",
            sa.String(50),
            nullable=False,
            server_default="UTC",
            comment="IANA timezone identifier (e.g. America/New_York)",
        ),
        sa.Column(
            "language",
            sa.String(10),
            nullable=False,
            server_default="en",
            comment="Locale / language code (e.g. en, es, fr)",
        ),
        sa.Column(
            "default_model",
            sa.String(100),
            nullable=False,
            server_default="gpt-4o",
            comment="Default AI model for new agents and chat sessions",
        ),
        sa.Column(
            "default_agent_id",
            sa.Uuid(),
            nullable=True,
            comment="Default agent to load on the agents page",
        ),
        # Notification preferences
        sa.Column(
            "notify_email_task_reminders",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notify_email_agent_completion",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notify_email_document_processing",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notify_email_knowledge_indexing",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "notify_browser_task_reminders",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "notify_browser_agent_completion",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        # Appearance settings
        sa.Column(
            "accent_color",
            sa.String(20),
            nullable=False,
            server_default="indigo",
            comment="Accent color: indigo, emerald, amber, rose, violet, sky",
        ),
        sa.Column(
            "sidebar_default_open",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "density",
            sa.String(20),
            nullable=False,
            server_default="comfortable",
            comment='UI density: "comfortable" or "compact"',
        ),
        sa.Column(
            "animations_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "font_scale",
            sa.Integer(),
            nullable=False,
            server_default="100",
            comment="Font size scale percentage (75–150)",
        ),
        # Extensible JSONB for future/custom settings
        sa.Column(
            "extra_settings",
            JSONB(),
            nullable=True,
            comment="Future/custom settings not yet covered by typed columns",
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=sa.func.now(),
        ),
        # PK constraint
        sa.PrimaryKeyConstraint("id"),
    )

    # ── api_provider_configs ─────────────────────────────────────────────────────
    op.create_table(
        "api_provider_configs",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to users.id",
        ),
        # Provider identity
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Provider slug: openai, anthropic, gemini, openrouter, groq, azure_openai, ollama",
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=True,
            comment="Optional human-readable label",
        ),
        # Credentials (encrypted)
        sa.Column(
            "api_key_encrypted",
            sa.String(500),
            nullable=False,
            comment="Fernet-encrypted API key — never decrypted in API responses",
        ),
        # Provider-specific config
        sa.Column(
            "config",
            JSONB(),
            nullable=True,
            comment="Provider-specific config: base_url, org_id, azure_endpoint, etc.",
        ),
        # State
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Display order (lower = first)",
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=sa.func.now(),
        ),
        # PK constraint
        sa.PrimaryKeyConstraint("id"),
        # Unique per user per provider
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )

    # ── user_sessions ────────────────────────────────────────────────────────────
    op.create_table(
        "user_sessions",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to users.id",
        ),
        # Session identity
        sa.Column(
            "jti",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="JWT ID — links this session to a refresh token",
        ),
        # Client info
        sa.Column(
            "device_name",
            sa.String(255),
            nullable=True,
            comment="User-facing device label",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="Client IP address (IPv4 or IPv6)",
        ),
        sa.Column(
            "user_agent",
            sa.String(500),
            nullable=True,
            comment="Raw User-Agent header",
        ),
        # State
        sa.Column(
            "is_current",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of manual revocation",
        ),
        # Timestamps (TimestampMixin)
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=sa.func.now(),
        ),
        # PK constraint
        sa.PrimaryKeyConstraint("id"),
    )

    # ── User table additions ─────────────────────────────────────────────────────
    # NOTE: `last_login_at` and `two_factor_enabled` were already created
    # by migration 000 (which builds users from the ORM model).  They are
    # omitted here to avoid duplicate-column errors.


def downgrade() -> None:
    # Drop tables (reverse order of creation)
    op.drop_table("user_sessions")
    op.drop_table("api_provider_configs")
    op.drop_table("user_settings")
