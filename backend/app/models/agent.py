"""AI Agent ORM models.

Represents autonomous AI agents with execution history, memory,
tool configuration, and reusable templates. Follows the same
UUIDMixin + TimestampMixin pattern used across all Aevix models.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Agent ────────────────────────────────────────────────────────────────────


class Agent(UUIDMixin, TimestampMixin, Base):
    """An autonomous AI agent owned by a user.

    Each agent has its own system prompt, model configuration,
    tool set, and memory. Agents are the top-level entity that
    users create, configure, and run.
    """

    __tablename__ = "agents"

    # ── Ownership ───────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),
        nullable=True,
        comment="Future multi-workspace support (reserved)",
    )

    # ── Core fields ─────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Agent display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short description of the agent's purpose",
    )
    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="System prompt that defines the agent's persona and behaviour",
    )

    # ── AI Model config ─────────────────────────────────────────────
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gpt-4o",
        comment="AI model identifier (e.g. gpt-4o, claude-3-opus)",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.7,
        comment="Model temperature (0.0–2.0)",
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum tokens per response",
    )

    # ── State ───────────────────────────────────────────────────────
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the agent is active and can be run",
    )

    # ── Relationships ───────────────────────────────────────────────
    owner: Mapped[User] = relationship(
        "User",
        back_populates="agents",
    )
    runs: Mapped[list[AgentRun]] = relationship(
        "AgentRun",
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentRun.created_at.desc()",
    )
    memories: Mapped[list[AgentMemory]] = relationship(
        "AgentMemory",
        back_populates="agent",
        cascade="all, delete-orphan",
    )
    tools: Mapped[list[AgentTool]] = relationship(
        "AgentTool",
        back_populates="agent",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Agent id={self.id} name={self.name!r} "
            f"model={self.model!r} enabled={self.enabled}>"
        )


# ── Agent Run ────────────────────────────────────────────────────────────────


class AgentRun(UUIDMixin, TimestampMixin, Base):
    """A single execution run of an agent.

    Tracks the full lifecycle of an agent invocation including
    status transitions, token usage, execution logs, and the
    final result.
    """

    __tablename__ = "agent_runs"

    # ── Foreign keys ────────────────────────────────────────────────
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Execution state ─────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="queued",
        comment="Run status: queued, running, paused, completed, failed, cancelled, timed_out",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when execution started",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when execution finished",
    )

    # ── Input / Output ──────────────────────────────────────────────
    input_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User-provided input that triggered this run",
    )
    result: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Final output produced by the agent",
    )

    # ── Execution metadata ──────────────────────────────────────────
    token_usage: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Token usage breakdown: {prompt, completion, total}",
    )
    cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Estimated cost of this run in USD",
    )
    steps: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Step-by-step execution plan and reasoning trace",
    )
    logs: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Execution log entries: [{timestamp, level, message, ...}]",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if the run failed or was cancelled",
    )

    # ── Relationships ───────────────────────────────────────────────
    agent: Mapped[Agent] = relationship(
        "Agent",
        back_populates="runs",
    )
    owner: Mapped[User] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentRun id={self.id} agent_id={self.agent_id} "
            f"status={self.status!r}>"
        )


# ── Agent Memory ─────────────────────────────────────────────────────────────


class AgentMemory(UUIDMixin, TimestampMixin, Base):
    """Memory entry stored by an agent during or between runs.

    Supports three memory types:
    - short_term: Recent contextual memory (ephemeral, pruned automatically)
    - long_term: Persistent knowledge accumulated across runs
    - conversation: Full conversation turns for context retention
    """

    __tablename__ = "agent_memories"

    # ── Foreign keys ────────────────────────────────────────────────
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to the run that created this memory",
    )

    # ── Memory data ─────────────────────────────────────────────────
    memory_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="short_term",
        comment="Memory type: short_term, long_term, conversation",
    )
    role: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Role if this is a conversation memory: user, assistant, system",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Memory content text",
    )
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional compressed summary of the memory",
    )
    memory_metadata: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        comment="Arbitrary metadata associated with this memory entry",
    )
    importance: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        default=0.0,
        comment="Importance score (0.0–1.0) for memory retention decisions",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional TTL — memory is eligible for pruning after this time",
    )

    # ── Relationships ───────────────────────────────────────────────
    agent: Mapped[Agent] = relationship(
        "Agent",
        back_populates="memories",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentMemory id={self.id} agent_id={self.agent_id} "
            f"type={self.memory_type!r}>"
        )


# ── Agent Tool ───────────────────────────────────────────────────────────────


class AgentTool(UUIDMixin, TimestampMixin, Base):
    """A tool configured for use by an agent.

    Tools are pluggable capabilities that agents can invoke during
    execution (e.g. knowledge search, document reading, task creation).
    Each tool stores its type, display name, description, and
    type-specific configuration.
    """

    __tablename__ = "agent_tools"

    # ── Foreign keys ────────────────────────────────────────────────
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Tool config ─────────────────────────────────────────────────
    tool_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Tool type identifier: knowledge_search, document_reader, task_manager, global_search, chat_history, calculator, current_time",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable tool name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of what this tool does (used by the agent to decide when to use it)",
    )
    config: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Tool-specific configuration (e.g. kb_id, max_results)",
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this tool is active",
    )

    # ── Relationships ───────────────────────────────────────────────
    agent: Mapped[Agent] = relationship(
        "Agent",
        back_populates="tools",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentTool id={self.id} agent_id={self.agent_id} "
            f"type={self.tool_type!r} name={self.name!r}>"
        )


# ── Agent Template ───────────────────────────────────────────────────────────


class AgentTemplate(UUIDMixin, TimestampMixin, Base):
    """A reusable agent template for quick agent creation.

    Templates define default configurations (system prompt, model,
    temperature, tool set) that users can clone when creating new
    agents. Built-in templates are seeded by the application and
    cannot be modified.
    """

    __tablename__ = "agent_templates"

    # ── Ownership ───────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Creator of custom templates (NULL for built-in)",
    )

    # ── Template data ───────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Template display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Short description of the template",
    )
    category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="general",
        comment="Template category: general, research, coding, writing, assistant, custom",
    )
    system_prompt: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Default system prompt for agents created from this template",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="gpt-4o",
        comment="Default model",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.7,
        comment="Default temperature",
    )
    default_tools: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Default tool set: [{tool_type, name, description, config}]",
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a system-provided template (cannot be modified)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this template is available for use",
    )

    # ── Relationships ───────────────────────────────────────────────
    owner: Mapped[User | None] = relationship(
        "User",
        back_populates="agent_templates",
    )

    def __repr__(self) -> str:
        return (
            f"<AgentTemplate id={self.id} name={self.name!r} "
            f"category={self.category!r} builtin={self.is_builtin}>"
        )


# ── Late imports (avoid circular dependencies) ──────────────────────────────
from app.models.user import User  # noqa: E402, F811
