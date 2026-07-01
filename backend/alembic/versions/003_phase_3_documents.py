"""Phase 3 — Add checksum and processing_status to files table.

Revision ID: 003
Revises: 002
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "files",
        sa.Column(
            "checksum",
            sa.String(64),
            nullable=True,
            comment="SHA-256 hex digest of file content",
        ),
    )
    op.add_column(
        "files",
        sa.Column(
            "processing_status",
            sa.String(32),
            server_default=sa.text("'completed'"),
            nullable=False,
            comment="Processing status: pending, processing, completed, failed",
        ),
    )


def downgrade() -> None:
    op.drop_column("files", "processing_status")
    op.drop_column("files", "checksum")
