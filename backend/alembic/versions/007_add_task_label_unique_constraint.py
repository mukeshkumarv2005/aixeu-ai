"""Add unique constraint on task_labels (task_id, name).

Prevents duplicate label names on the same task at the database level.
Back-end validation already catches this at the service layer.

Revision ID: 007
Revises: 006
Create Date: 2026-07-02
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_task_labels_task_name",
        "task_labels",
        ["task_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_task_labels_task_name", "task_labels", type_="unique")
