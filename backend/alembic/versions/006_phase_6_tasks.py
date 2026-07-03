"""Phase 6 — Task Management tables.

Creates ``tasks``, ``task_comments``, ``task_labels``, and
``task_attachments`` tables for the AI-powered task management
system.  Supports Kanban-style workflows, scheduling, labels,
comments, and file attachments.

Revision ID: 006
Revises: 005
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tasks ────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
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
            nullable=False,
            comment="FK to users.id",
        ),
        # Core fields
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            comment="Short task title",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Long-form task description / notes",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'todo'"),
            comment="Task status: todo, in_progress, review, done, archived",
        ),
        sa.Column(
            "priority",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'medium'"),
            comment="Task priority: low, medium, high, critical",
        ),
        # Scheduling
        sa.Column(
            "due_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Optional due date for the task",
        ),
        sa.Column(
            "reminder_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Optional reminder datetime",
        ),
        sa.Column(
            "estimated_minutes",
            sa.Integer(),
            nullable=True,
            comment="Estimated effort in minutes",
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when the task was moved to 'done'",
        ),
        # Optional links
        sa.Column(
            "uploaded_document_id",
            sa.Uuid(),
            nullable=True,
            comment="Optional link to an uploaded File",
        ),
        sa.Column(
            "chat_conversation_id",
            sa.Uuid(),
            nullable=True,
            comment="Optional link to an AI chat conversation",
        ),
        sa.Column(
            "kb_document_id",
            sa.Uuid(),
            nullable=True,
            comment="Optional link to a knowledge-base document",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # PK / FK constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_document_id"],
            ["files.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["chat_conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["kb_document_id"],
            ["kb_documents.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.create_index(
        "ix_tasks_uploaded_document_id",
        "tasks",
        ["uploaded_document_id"],
    )
    op.create_index(
        "ix_tasks_chat_conversation_id",
        "tasks",
        ["chat_conversation_id"],
    )
    op.create_index(
        "ix_tasks_kb_document_id",
        "tasks",
        ["kb_document_id"],
    )

    # ── task_comments ────────────────────────────────────────────────────────
    op.create_table(
        "task_comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "task_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to tasks.id",
        ),
        sa.Column(
            "author_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to users.id",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Comment body text",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_task_comments_task_id", "task_comments", ["task_id"])
    op.create_index("ix_task_comments_author_id", "task_comments", ["author_id"])

    # ── task_labels ──────────────────────────────────────────────────────────
    op.create_table(
        "task_labels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "task_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to tasks.id",
        ),
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Label display text (e.g. 'bug', 'feature')",
        ),
        sa.Column(
            "color",
            sa.String(50),
            nullable=True,
            comment="Optional hex colour code (e.g. '#ff0000')",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_task_labels_task_id", "task_labels", ["task_id"])

    # ── task_attachments ─────────────────────────────────────────────────────
    op.create_table(
        "task_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "task_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to tasks.id",
        ),
        sa.Column(
            "file_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to files.id",
        ),
        sa.Column(
            "uploaded_by",
            sa.Uuid(),
            nullable=False,
            comment="FK to users.id",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_task_attachments_task_id",
        "task_attachments",
        ["task_id"],
    )
    op.create_index(
        "ix_task_attachments_file_id",
        "task_attachments",
        ["file_id"],
    )
    op.create_index(
        "ix_task_attachments_uploaded_by",
        "task_attachments",
        ["uploaded_by"],
    )


def downgrade() -> None:
    op.drop_table("task_attachments")
    op.drop_table("task_labels")
    op.drop_table("task_comments")
    op.drop_table("tasks")
