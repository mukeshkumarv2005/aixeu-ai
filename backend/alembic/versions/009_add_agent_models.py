"""Add AI Agent tables.

Creates ``agents``, ``agent_runs``, ``agent_memories``,
``agent_tools``, and ``agent_templates`` tables to support
the autonomous AI Agent framework.

Revision ID: 009
Revises: 008
Create Date: 2026-07-03
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agents ───────────────────────────────────────────────────────────────────
    op.create_table(
        "agents",
        # PK (UUIDMixin)
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
            index=True,
            comment="FK to users.id",
        ),
        # Core fields
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Agent display name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Short description of the agent's purpose",
        ),
        sa.Column(
            "system_prompt",
            sa.Text(),
            nullable=True,
            comment="System prompt that defines the agent's persona and behaviour",
        ),
        # AI Model config
        sa.Column(
            "model",
            sa.String(100),
            nullable=False,
            server_default="gpt-4o",
            comment="AI model identifier",
        ),
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0.7",
            comment="Model temperature (0.0–2.0)",
        ),
        sa.Column(
            "max_tokens",
            sa.Integer(),
            nullable=True,
            comment="Maximum tokens per response",
        ),
        # State
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether the agent is active and can be run",
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

    # ── agent_runs ───────────────────────────────────────────────────────────────
    op.create_table(
        "agent_runs",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Foreign keys
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="FK to agents.id",
        ),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="FK to users.id",
        ),
        # Execution state
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="queued",
            comment="Run status: queued, running, paused, completed, failed, cancelled, timed_out",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when execution started",
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when execution finished",
        ),
        # Input / Output
        sa.Column(
            "input_text",
            sa.Text(),
            nullable=True,
            comment="User-provided input that triggered this run",
        ),
        sa.Column(
            "result",
            sa.Text(),
            nullable=True,
            comment="Final output produced by the agent",
        ),
        # Execution metadata
        sa.Column(
            "token_usage",
            JSONB(),
            nullable=True,
            comment="Token usage breakdown: {prompt, completion, total}",
        ),
        sa.Column(
            "cost",
            sa.Float(),
            nullable=True,
            comment="Estimated cost of this run in USD",
        ),
        sa.Column(
            "steps",
            JSONB(),
            nullable=True,
            comment="Step-by-step execution plan and reasoning trace",
        ),
        sa.Column(
            "logs",
            JSONB(),
            nullable=True,
            comment="Execution log entries: [{timestamp, level, message, ...}]",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Error message if the run failed or was cancelled",
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

    # ── agent_memories ───────────────────────────────────────────────────────────
    op.create_table(
        "agent_memories",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Foreign keys
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="FK to agents.id",
        ),
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("agent_runs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Optional link to the run that created this memory",
        ),
        # Memory data
        sa.Column(
            "memory_type",
            sa.String(20),
            nullable=False,
            server_default="short_term",
            comment="Memory type: short_term, long_term, conversation",
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=True,
            comment="Role if conversation memory: user, assistant, system",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Memory content text",
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
            comment="Optional compressed summary of the memory",
        ),
        sa.Column(
            "metadata",
            JSONB(),
            nullable=True,
            comment="Arbitrary metadata associated with this memory entry",
        ),
        sa.Column(
            "importance",
            sa.Float(),
            nullable=True,
            server_default="0.0",
            comment="Importance score (0.0–1.0) for memory retention decisions",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Optional TTL for memory pruning",
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

    # ── agent_tools ──────────────────────────────────────────────────────────────
    op.create_table(
        "agent_tools",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Foreign keys
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="FK to agents.id",
        ),
        # Tool config
        sa.Column(
            "tool_type",
            sa.String(50),
            nullable=False,
            comment="Tool type identifier",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable tool name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Description of what this tool does",
        ),
        sa.Column(
            "config",
            JSONB(),
            nullable=True,
            comment="Tool-specific configuration",
        ),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether this tool is active",
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

    # ── agent_templates ──────────────────────────────────────────────────────────
    op.create_table(
        "agent_templates",
        # PK (UUIDMixin)
        sa.Column("id", sa.Uuid(), nullable=False),
        # Ownership
        sa.Column(
            "owner_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
            comment="Creator of custom templates (NULL for built-in)",
        ),
        # Template data
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Template display name",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Short description of the template",
        ),
        sa.Column(
            "category",
            sa.String(50),
            nullable=True,
            server_default="general",
            comment="Template category: general, research, coding, writing, assistant, custom",
        ),
        sa.Column(
            "system_prompt",
            sa.Text(),
            nullable=True,
            comment="Default system prompt for agents created from this template",
        ),
        sa.Column(
            "model",
            sa.String(100),
            nullable=False,
            server_default="gpt-4o",
            comment="Default model",
        ),
        sa.Column(
            "temperature",
            sa.Float(),
            nullable=False,
            server_default="0.7",
            comment="Default temperature",
        ),
        sa.Column(
            "default_tools",
            JSONB(),
            nullable=True,
            comment="Default tool set: [{tool_type, name, description, config}]",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Whether this is a system-provided template (cannot be modified)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether this template is available for use",
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


def downgrade() -> None:
    op.drop_table("agent_templates")
    op.drop_table("agent_tools")
    op.drop_table("agent_memories")
    op.drop_table("agent_runs")
    op.drop_table("agents")
