"""Pydantic schemas for the Task Management system.

Covers CRUD operations for tasks, comments, labels, and attachments.
All schemas use ``from_attributes = True`` for ORM compatibility.

Validation rules:
- Past dates are rejected for new tasks (due_date, reminder_at).
- reminder_at must not be after due_date when both are provided.
- Status values are enumerated in TASK_STATUSES.
- Priority values are enumerated in TASK_PRIORITIES.
- Label colours must be valid hex codes (#rgb or #rrggbb).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Constants ────────────────────────────────────────────────────────────────

TASK_STATUSES = frozenset({"todo", "in_progress", "review", "done", "archived"})
TASK_PRIORITIES = frozenset({"low", "medium", "high", "critical"})
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


# ── Shared validation helpers ────────────────────────────────────────────────


def _reject_past_dates(
    due_date: datetime | None,
    reminder_at: datetime | None,
) -> None:
    """Raise ``ValueError`` if a date is in the past (for new-task creation)."""
    now = datetime.now(timezone.utc)
    if due_date is not None and due_date < now:
        raise ValueError("due_date must not be in the past")
    if reminder_at is not None and reminder_at < now:
        raise ValueError("reminder_at must not be in the past")
    if (
        due_date is not None
        and reminder_at is not None
        and reminder_at > due_date
    ):
        raise ValueError("reminder_at must not be after due_date")


def _validate_hex_color(v: str | None) -> str | None:
    """Reject colour values that are not valid hex codes."""
    if v is not None and not HEX_COLOR_RE.match(v):
        raise ValueError(
            f"Invalid colour '{v}'. Must be a hex code like #ff0000 or #f00."
        )
    return v


# ── Task ─────────────────────────────────────────────────────────────────────


class TaskCreate(BaseModel):
    """Request to create a new task."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Short task title",
    )
    description: str | None = Field(
        None,
        max_length=100000,
        description="Long-form task description / notes",
    )
    status: str = Field(
        default="todo",
        description="Task status",
    )
    priority: str = Field(
        default="medium",
        description="Task priority",
    )
    due_date: datetime | None = Field(
        None,
        description="Optional due date (ISO 8601)",
    )
    reminder_at: datetime | None = Field(
        None,
        description="Optional reminder datetime (ISO 8601)",
    )
    estimated_minutes: int | None = Field(
        None,
        ge=0,
        le=525600,  # 1 year in minutes
        description="Estimated effort in minutes",
    )
    uploaded_document_id: UUID | None = Field(
        None,
        description="Optional link to an uploaded File (UUID)",
    )
    chat_conversation_id: UUID | None = Field(
        None,
        description="Optional link to an AI chat conversation (UUID)",
    )
    kb_document_id: UUID | None = Field(
        None,
        description="Optional link to a knowledge-base document (UUID)",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.lower().replace(" ", "_")
        if v not in TASK_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(TASK_STATUSES))}"
            )
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        v = v.lower()
        if v not in TASK_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{v}'. Must be one of: {', '.join(sorted(TASK_PRIORITIES))}"
            )
        return v

    @field_validator("due_date", "reminder_at")
    @classmethod
    def validate_dates_create(cls, v: datetime | None, info) -> datetime | None:
        """Validate dates on creation: no past dates, no reminder after due."""
        if v is not None:
            # Collect both values from the validation context
            values = info.data
            due = values.get("due_date") if info.field_name == "reminder_at" else v
            reminder = v if info.field_name == "reminder_at" else values.get("reminder_at")
            _reject_past_dates(
                due_date=due if info.field_name == "due_date" else values.get("due_date"),
                reminder_at=reminder if info.field_name == "reminder_at" else v,
            )
        return v


class TaskUpdate(BaseModel):
    """Request to update an existing task (partial update)."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    reminder_at: datetime | None = None
    estimated_minutes: int | None = None
    uploaded_document_id: UUID | None = None
    chat_conversation_id: UUID | None = None
    kb_document_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.lower().replace(" ", "_")
        if v not in TASK_STATUSES:
            raise ValueError(
                f"Invalid status '{v}'. Must be one of: {', '.join(sorted(TASK_STATUSES))}"
            )
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.lower()
        if v not in TASK_PRIORITIES:
            raise ValueError(
                f"Invalid priority '{v}'. Must be one of: {', '.join(sorted(TASK_PRIORITIES))}"
            )
        return v


class TaskLabelSchema(BaseModel):
    """Label attached to a task (read / write)."""

    id: UUID | None = None
    name: str = Field(..., min_length=1, max_length=100, description="Label name")
    color: str | None = Field(None, max_length=50, description="Hex colour code")

    @field_validator("color", mode="before")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Reject colour values that are not valid hex codes."""
        return _validate_hex_color(v)

    model_config = {"from_attributes": True}


class TaskCommentSchema(BaseModel):
    """Comment on a task (read response)."""

    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskCommentCreate(BaseModel):
    """Request to create a new comment on a task."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Comment body text",
    )


class TaskAttachmentSchema(BaseModel):
    """Attachment on a task (read response)."""

    id: UUID
    task_id: UUID
    file_id: UUID
    uploaded_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Full task read response."""

    id: UUID
    owner_id: UUID
    title: str
    description: str | None = None
    status: str
    priority: str
    due_date: datetime | None = None
    reminder_at: datetime | None = None
    estimated_minutes: int | None = None
    completed_at: datetime | None = None
    uploaded_document_id: UUID | None = None
    chat_conversation_id: UUID | None = None
    kb_document_id: UUID | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # Nested relations (included only when requested / available)
    labels: list[TaskLabelSchema] = Field(default_factory=list)
    comments: list[TaskCommentSchema] = Field(default_factory=list)
    attachments: list[TaskAttachmentSchema] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    items: list[TaskResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of matching tasks")
    offset: int = Field(default=0, description="Offset used for this page")
    limit: int = Field(default=50, description="Limit used for this page")


# ── Dashboard / Stats ───────────────────────────────────────────────────────


class TaskBoardResponse(BaseModel):
    """Tasks grouped by status column for Kanban board view."""

    todo: list[TaskResponse] = Field(default_factory=list)
    in_progress: list[TaskResponse] = Field(default_factory=list)
    review: list[TaskResponse] = Field(default_factory=list)
    done: list[TaskResponse] = Field(default_factory=list)
    archived: list[TaskResponse] = Field(default_factory=list)


class TaskCalendarResponse(BaseModel):
    """Tasks with due dates in a given date range for calendar view."""

    items: list[TaskResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total matching tasks")
    start_date: datetime | None = Field(None, description="Start of queried range")
    end_date: datetime | None = Field(None, description="End of queried range")


class TaskStats(BaseModel):
    """Aggregate task statistics for the current user."""

    total: int = Field(default=0, description="Total tasks")
    todo: int = Field(default=0, description="Tasks with status 'todo'")
    in_progress: int = Field(default=0, description="Tasks with status 'in_progress'")
    review: int = Field(default=0, description="Tasks with status 'review'")
    done: int = Field(default=0, description="Tasks with status 'done'")
    archived: int = Field(default=0, description="Tasks with status 'archived'")
    overdue: int = Field(default=0, description="Tasks past due_date and not done/archived")
    critical: int = Field(default=0, description="Tasks with priority 'critical'")
    high: int = Field(default=0, description="Tasks with priority 'high'")
    medium: int = Field(default=0, description="Tasks with priority 'medium'")
    low: int = Field(default=0, description="Tasks with priority 'low'")
    incomplete_by_priority: dict[str, int] = Field(
        default_factory=dict,
        description="Count of incomplete tasks grouped by priority level",
    )
