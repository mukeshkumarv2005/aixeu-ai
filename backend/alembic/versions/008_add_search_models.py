"""Add search-related tables for Global Search.

Creates ``saved_searches`` and ``recent_searches`` tables to support
the global search feature across Chats, Documents, Knowledge Base,
and Tasks.

Revision ID: 008
Revises: 007
Create Date: 2026-07-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── saved_searches ─────────────────────────────────────────────────────────
    op.create_table(
        "saved_searches",
        # PK
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            nullable=True,
            comment="Future multi-workspace support (reserved)",
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to users.id",
            index=True,
        ),
        # Search data
        sa.Column(
            "query",
            sa.String(1024),
            nullable=False,
            comment="The search query text",
        ),
        sa.Column(
            "filters",
            sa.JSON(),
            nullable=True,
            comment="Optional filters as JSON (status, priority, date ranges, etc.)",
        ),
        # Timestamps (from TimestampMixin)
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

    # ── recent_searches ────────────────────────────────────────────────────────
    op.create_table(
        "recent_searches",
        # PK
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            nullable=True,
            comment="Future multi-workspace support (reserved)",
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to users.id",
            index=True,
        ),
        # Search data
        sa.Column(
            "query",
            sa.String(1024),
            nullable=False,
            comment="The search query text",
        ),
        # Timestamp
        sa.Column(
            "searched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="When the search was performed",
        ),
        # PK constraint
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("recent_searches")
    op.drop_table("saved_searches")
