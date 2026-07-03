"""Task management ORM models.

Represents user-owned tasks with priorities, due dates, labels,
comments, file attachments, and optional links to documents,
conversations, and knowledge-base entries.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.file import File
    from app.models.conversation import Conversation
    from app.models.knowledge import KnowledgeBaseDocument
    from app.models.user import User


# ── Task ────────────────────────────────────────────────────────────────────


class Task(UUIDMixin, TimestampMixin, Base):
    """A single task owned by a user.

    Supports kanban-style status tracking, priority levels, due dates,
    reminders, and optional links to files, conversations, and KB docs.
    """

    __tablename__ = "tasks"

    # ── Ownership ───────────────────────────────────────────────────
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),  # type: ignore[name-defined]
        nullable=True,
        comment="Future multi-workspace support (reserved)",
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ─────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Short task title",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Long-form task description / notes",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="todo",
        comment="Task status: todo, in_progress, review, done, archived",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        comment="Task priority: low, medium, high, critical",
    )

    # ── Scheduling ──────────────────────────────────────────────────
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional due date for the task",
    )
    reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Optional reminder datetime",
    )
    estimated_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Estimated effort in minutes",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the task was moved to 'done'",
    )

    # ── Optional links ──────────────────────────────────────────────
    uploaded_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to an uploaded File",
    )
    chat_conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to an AI chat conversation",
    )
    kb_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("kb_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to a knowledge-base document",
    )

    # ── Relationships ───────────────────────────────────────────────
    owner: Mapped[User] = relationship(
        "User",
        back_populates="tasks",
    )
    comments: Mapped[list[TaskComment]] = relationship(
        "TaskComment",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskComment.created_at",
    )
    labels: Mapped[list[TaskLabel]] = relationship(
        "TaskLabel",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list[TaskAttachment]] = relationship(
        "TaskAttachment",
        back_populates="task",
        cascade="all, delete-orphan",
    )
    uploaded_document: Mapped[File | None] = relationship(
        "File",
        back_populates="tasks",
    )
    chat_conversation: Mapped[Conversation | None] = relationship(
        "Conversation",
        back_populates="tasks",
    )
    kb_document: Mapped[KnowledgeBaseDocument | None] = relationship(
        "KnowledgeBaseDocument",
        back_populates="tasks",
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} title={self.title!r} "
            f"status={self.status!r} priority={self.priority!r}>"
        )


# ── Task Comment ────────────────────────────────────────────────────────────


class TaskComment(UUIDMixin, TimestampMixin, Base):
    """A comment / discussion entry on a task."""

    __tablename__ = "task_comments"

    # ── Foreign keys ────────────────────────────────────────────────
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Content ─────────────────────────────────────────────────────
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Comment body text",
    )

    # ── Relationships ───────────────────────────────────────────────
    task: Mapped[Task] = relationship(
        "Task",
        back_populates="comments",
    )
    author: Mapped[User] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return (
            f"<TaskComment id={self.id} task_id={self.task_id} "
            f"author_id={self.author_id}>"
        )


# ── Task Label ─────────────────────────────────────────────────────────────


class TaskLabel(UUIDMixin, Base):
    """A label / tag attached to a task.

    Labels are lightweight — they carry a display name and optional
    hex colour but do not have their own CRUD lifecycle (they exist
    only as children of a task).
    """

    __tablename__ = "task_labels"
    __table_args__ = (
        UniqueConstraint("task_id", "name", name="uq_task_labels_task_name"),
    )

    # ── Foreign keys ────────────────────────────────────────────────
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Data ────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Label display text (e.g. 'bug', 'feature')",
    )
    color: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Optional hex colour code (e.g. '#ff0000')",
    )

    # ── Timestamp ───────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────
    task: Mapped[Task] = relationship(
        "Task",
        back_populates="labels",
    )

    def __repr__(self) -> str:
        return f"<TaskLabel id={self.id} name={self.name!r}>"


# ── Task Attachment ─────────────────────────────────────────────────────────


class TaskAttachment(UUIDMixin, Base):
    """A file attached to a task.

    Delegates the actual file storage to the existing File model
    (which handles uploads, storage back-ends, and processing).
    """

    __tablename__ = "task_attachments"

    # ── Foreign keys ────────────────────────────────────────────────
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Timestamp ───────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────
    task: Mapped[Task] = relationship(
        "Task",
        back_populates="attachments",
    )
    file: Mapped[File] = relationship(
        "File",
    )
    uploader: Mapped[User] = relationship(
        "User",
    )

    def __repr__(self) -> str:
        return (
            f"<TaskAttachment id={self.id} task_id={self.task_id} "
            f"file_id={self.file_id}>"
        )


# ── Late imports (avoid circular dependencies) ──────────────────────────────
from app.models.conversation import Conversation  # noqa: E402, F811
from app.models.file import File  # noqa: E402, F811
from app.models.knowledge import KnowledgeBaseDocument  # noqa: E402, F811
from app.models.user import User  # noqa: E402, F811
