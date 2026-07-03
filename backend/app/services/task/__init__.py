"""Task management service — CRUD, labels, comments, attachments, and stats.

The ``TaskService`` encapsulates all business logic for tasks, enforcing
ownership isolation on every query.  Callers pass the authenticated
user's ID to every method.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import AppException
from app.models.conversation import Conversation
from app.models.file import File
from app.models.knowledge import KnowledgeBase, KnowledgeBaseDocument
from app.models.task import Task, TaskAttachment, TaskComment, TaskLabel
from app.models.user import User
from app.schemas.task import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    TaskAttachmentSchema,
    TaskBoardResponse,
    TaskCalendarResponse,
    TaskCommentCreate,
    TaskCommentSchema,
    TaskCreate,
    TaskLabelSchema,
    TaskListResponse,
    TaskResponse,
    TaskStats,
    TaskUpdate,
)


# ── Exceptions ─────────────────────────────────────────────────────────────────


class TaskNotFound(AppException):
    def __init__(self, task_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Task {task_id} not found")


class FileNotFound(AppException):
    def __init__(self, file_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"File {file_id} not found")


class CommentNotFound(AppException):
    def __init__(self, comment_id: uuid.UUID) -> None:
        super().__init__(
            status_code=404, detail=f"Comment {comment_id} not found"
        )


class LabelNotFound(AppException):
    def __init__(self, label_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Label {label_id} not found")


class LabelAlreadyExists(AppException):
    def __init__(self, task_id: uuid.UUID, name: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"Label '{name}' already exists on task {task_id}",
        )


class AttachmentNotFound(AppException):
    def __init__(self, attachment_id: uuid.UUID) -> None:
        super().__init__(
            status_code=404, detail=f"Attachment {attachment_id} not found"
        )


class InvalidTransition(AppException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            status_code=400,
            detail=f"Cannot transition task from '{current}' to '{target}'",
        )


# ── Constants ──────────────────────────────────────────────────────────────────

# Allowed status transitions: {current_status: {target_status, ...}}
# Any transition not listed here (including self → self) is rejected.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"in_progress", "done", "archived"},
    "in_progress": {"review", "done", "archived", "todo"},
    "review": {"in_progress", "done", "archived", "todo"},
    "done": {"archived", "todo"},
    "archived": {"todo"},  # unarchive — must go through restore endpoint
}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _apply_list_filters(
    stmt: Select,
    *,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
) -> Select:
    """Apply optional status / priority / search filters to a task SELECT."""
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(Task.title.ilike(like), Task.description.ilike(like))
        )
    return stmt


async def _fetch_task_or_raise(
    db: AsyncSession,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    options: bool = False,
) -> Task:
    """Fetch a task by id, raising 404 if not found or not owned by user."""
    stmt = select(Task).where(Task.id == task_id, Task.owner_id == user_id)
    if options:
        stmt = stmt.options(
            joinedload(Task.labels),
            joinedload(Task.comments),
            joinedload(Task.attachments),
        )
    result = await db.execute(stmt)
    task = result.unique().scalar_one_or_none()
    if task is None:
        raise TaskNotFound(task_id)
    return task


def _to_task_response(task: Task) -> TaskResponse:
    """Convert ORM Task to Pydantic response, including nested relations."""
    return TaskResponse(
        id=task.id,
        owner_id=task.owner_id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        due_date=task.due_date,
        reminder_at=task.reminder_at,
        estimated_minutes=task.estimated_minutes,
        completed_at=task.completed_at,
        uploaded_document_id=task.uploaded_document_id,
        chat_conversation_id=task.chat_conversation_id,
        kb_document_id=task.kb_document_id,
        created_at=task.created_at,
        updated_at=task.updated_at,
        labels=[TaskLabelSchema.model_validate(l) for l in (task.labels or [])],
        comments=[
            TaskCommentSchema.model_validate(c) for c in (task.comments or [])
        ],
        attachments=[
            TaskAttachmentSchema.model_validate(a)
            for a in (task.attachments or [])
        ],
    )


def _validate_transition(current: str, target: str) -> None:
    """Raise ``InvalidTransition`` if ``current → target`` is not allowed."""
    allowed = VALID_TRANSITIONS.get(current)
    if allowed is None or target not in allowed:
        raise InvalidTransition(current, target)


def _has_resource_link(data: TaskCreate | TaskUpdate) -> bool:
    """Return True if any resource-link FK is set in *data*."""
    return bool(
        data.uploaded_document_id
        or data.chat_conversation_id
        or data.kb_document_id
    )


# ── Service ────────────────────────────────────────────────────────────────────


class TaskService:
    """CRUD and business-logic operations for tasks, scoped to a user session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Resource validation ──────────────────────────────────────────────

    async def _check_resource_links(
        self,
        data: TaskCreate | TaskUpdate,
        user_id: uuid.UUID,
    ) -> None:
        """Verify that any resource-link FKs point to existing, user-owned
        records.  Raises ``AppException(404)`` if a resource is missing.
        """
        if data.uploaded_document_id is not None:
            result = await self.db.execute(
                select(File).where(
                    File.id == data.uploaded_document_id,
                    File.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise FileNotFound(data.uploaded_document_id)

        if data.chat_conversation_id is not None:
            result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == data.chat_conversation_id,
                    Conversation.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise AppException(
                    status_code=404,
                    detail=f"Conversation {data.chat_conversation_id} not found",
                )

        if data.kb_document_id is not None:
            result = await self.db.execute(
                select(KnowledgeBaseDocument)
                .join(KnowledgeBaseDocument.knowledge_base)
                .where(
                    KnowledgeBaseDocument.id == data.kb_document_id,
                    KnowledgeBase.user_id == user_id,
                )
            )
            if result.scalar_one_or_none() is None:
                raise AppException(
                    status_code=404,
                    detail=f"Knowledge-base document {data.kb_document_id} not found",
                )

    # ── Task CRUD ──────────────────────────────────────────────────────

    async def create_task(
        self, data: TaskCreate, user_id: uuid.UUID
    ) -> TaskResponse:
        """Create a new task for the given user."""
        # Verify referenced resources exist and belong to user
        await self._check_resource_links(data, user_id)

        now = datetime.now(timezone.utc)
        task = Task(
            owner_id=user_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            due_date=data.due_date,
            reminder_at=data.reminder_at,
            estimated_minutes=data.estimated_minutes,
            uploaded_document_id=data.uploaded_document_id,
            chat_conversation_id=data.chat_conversation_id,
            kb_document_id=data.kb_document_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        # Re-fetch with eager-loaded relations for response serialization
        task = await _fetch_task_or_raise(self.db, task.id, user_id, options=True)
        return _to_task_response(task)

    async def get_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> TaskResponse:
        """Get a single task with all nested relations."""
        task = await _fetch_task_or_raise(
            self.db, task_id, user_id, options=True
        )
        return _to_task_response(task)

    async def update_task(
        self,
        task_id: uuid.UUID,
        data: TaskUpdate,
        user_id: uuid.UUID,
    ) -> TaskResponse:
        """Update an existing task (partial update)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)

        # Validate status transition
        if data.status is not None and data.status != task.status:
            _validate_transition(task.status, data.status)

        # Verify resource links exist and belong to user
        if _has_resource_link(data):
            await self._check_resource_links(data, user_id)

        # Build the update dict from non-None fields
        update_fields: dict = {}
        for field in (
            "title",
            "description",
            "status",
            "priority",
            "due_date",
            "reminder_at",
            "estimated_minutes",
            "uploaded_document_id",
            "chat_conversation_id",
            "kb_document_id",
        ):
            value = getattr(data, field, None)
            if value is not None:
                update_fields[field] = value

        # Auto-set completed_at when status changes to "done"
        if (
            "status" in update_fields
            and update_fields["status"] == "done"
            and task.status != "done"
        ):
            update_fields["completed_at"] = datetime.now(timezone.utc)
        elif "status" in update_fields and update_fields["status"] != "done":
            update_fields["completed_at"] = None

        if update_fields:
            update_fields["updated_at"] = datetime.now(timezone.utc)
            stmt = (
                update(Task)
                .where(Task.id == task_id, Task.owner_id == user_id)
                .values(**update_fields)
            )
            await self.db.execute(stmt)
            await self.db.commit()

        return await self.get_task(task_id, user_id)

    async def delete_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete a task and all its children (cascade)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        await self.db.delete(task)
        await self.db.commit()

    async def list_tasks(
        self,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> TaskListResponse:
        """List tasks with optional filtering and pagination."""
        # Count
        count_stmt = select(func.count(Task.id)).where(
            Task.owner_id == user_id
        )
        count_stmt = _apply_list_filters(
            count_stmt, status=status, priority=priority, search=search
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # Fetch page
        query_stmt = (
            select(Task)
            .where(Task.owner_id == user_id)
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        query_stmt = _apply_list_filters(
            query_stmt, status=status, priority=priority, search=search
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def search_tasks(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> TaskListResponse:
        """Full-text-like search on task title and description."""
        return await self.list_tasks(
            user_id,
            search=query,
            offset=offset,
            limit=limit,
        )

    # ── Labels ─────────────────────────────────────────────────────────

    async def add_label(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        color: str | None = None,
    ) -> TaskLabelSchema:
        """Add a label to a task."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)

        # Reject duplicate label names on the same task
        existing = await self.db.execute(
            select(TaskLabel).where(
                TaskLabel.task_id == task.id,
                TaskLabel.name == name,
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise LabelAlreadyExists(task.id, name)

        label = TaskLabel(task_id=task.id, name=name, color=color)
        self.db.add(label)
        await self.db.commit()
        await self.db.refresh(label)
        return TaskLabelSchema.model_validate(label)

    async def remove_label(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        label_id: uuid.UUID,
    ) -> None:
        """Remove a label from a task (owner-gated via task ownership)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        stmt = select(TaskLabel).where(
            TaskLabel.id == label_id, TaskLabel.task_id == task.id
        )
        result = await self.db.execute(stmt)
        label = result.scalar_one_or_none()
        if label is None:
            raise LabelNotFound(label_id)
        await self.db.delete(label)
        await self.db.commit()

    # ── Comments ───────────────────────────────────────────────────────

    async def add_comment(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        data: TaskCommentCreate,
    ) -> TaskCommentSchema:
        """Add a comment to a task."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        now = datetime.now(timezone.utc)
        comment = TaskComment(
            task_id=task.id,
            author_id=user_id,
            content=data.content,
            created_at=now,
            updated_at=now,
        )
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return TaskCommentSchema.model_validate(comment)

    async def update_comment(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        comment_id: uuid.UUID,
        content: str,
    ) -> TaskCommentSchema:
        """Update the content of a comment (author-only)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        stmt = select(TaskComment).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task.id,
            TaskComment.author_id == user_id,
        )
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()
        if comment is None:
            raise CommentNotFound(comment_id)
        comment.content = content
        comment.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(comment)
        return TaskCommentSchema.model_validate(comment)

    async def delete_comment(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        comment_id: uuid.UUID,
    ) -> None:
        """Delete a comment (author or task-owner only)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        stmt = select(TaskComment).where(
            TaskComment.id == comment_id,
            TaskComment.task_id == task.id,
        )
        result = await self.db.execute(stmt)
        comment = result.scalar_one_or_none()
        if comment is None:
            raise CommentNotFound(comment_id)
        # Only the comment author or the task owner may delete
        if comment.author_id != user_id and task.owner_id != user_id:
            raise AppException(
                status_code=403,
                detail="Only the comment author or task owner can delete this comment",
            )
        await self.db.delete(comment)
        await self.db.commit()

    # ── Attachments ────────────────────────────────────────────────────

    async def add_attachment(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        file_id: uuid.UUID,
    ) -> TaskAttachmentSchema:
        """Attach a file to a task."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)

        # Verify file exists and belongs to user
        f_stmt = select(File).where(
            File.id == file_id, File.user_id == user_id
        )
        f_result = await self.db.execute(f_stmt)
        file_record = f_result.scalar_one_or_none()
        if file_record is None:
            raise FileNotFound(file_id)

        attachment = TaskAttachment(
            task_id=task.id,
            file_id=file_id,
            uploaded_by=user_id,
        )
        self.db.add(attachment)
        await self.db.commit()
        await self.db.refresh(attachment)
        return TaskAttachmentSchema.model_validate(attachment)

    async def remove_attachment(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        attachment_id: uuid.UUID,
    ) -> None:
        """Remove an attachment from a task."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        stmt = select(TaskAttachment).where(
            TaskAttachment.id == attachment_id,
            TaskAttachment.task_id == task.id,
        )
        result = await self.db.execute(stmt)
        attachment = result.scalar_one_or_none()
        if attachment is None:
            raise AttachmentNotFound(attachment_id)
        await self.db.delete(attachment)
        await self.db.commit()

    # ── Status transitions ────────────────────────────────────────────

    async def complete_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> TaskResponse:
        """Mark a task as done (idempotent if already done)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        if task.status != "done":
            now = datetime.now(timezone.utc)
            stmt = (
                update(Task)
                .where(Task.id == task_id, Task.owner_id == user_id)
                .values(status="done", completed_at=now, updated_at=now)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_task(task_id, user_id)

    async def archive_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> TaskResponse:
        """Archive a task (idempotent if already archived)."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        if task.status != "archived":
            now = datetime.now(timezone.utc)
            stmt = (
                update(Task)
                .where(Task.id == task_id, Task.owner_id == user_id)
                .values(status="archived", updated_at=now)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_task(task_id, user_id)

    async def restore_task(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> TaskResponse:
        """Restore an archived task back to its previous active status,
        defaulting to ``todo`` if the stored status is still ``archived``."""
        task = await _fetch_task_or_raise(self.db, task_id, user_id)
        if task.status == "archived":
            now = datetime.now(timezone.utc)
            stmt = (
                update(Task)
                .where(Task.id == task_id, Task.owner_id == user_id)
                .values(status="todo", updated_at=now)
            )
            await self.db.execute(stmt)
            await self.db.commit()
        return await self.get_task(task_id, user_id)

    # ── Board / Calendar ─────────────────────────────────────────────

    async def get_board(
        self, user_id: uuid.UUID, *, limit: int = 200
    ) -> TaskBoardResponse:
        """Return tasks grouped by status for Kanban board view."""
        stmt = (
            select(Task)
            .where(Task.owner_id == user_id)
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        tasks = result.unique().scalars().all()

        board: dict[str, list[TaskResponse]] = {
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": [],
            "archived": [],
        }
        for t in tasks:
            board.setdefault(t.status, []).append(_to_task_response(t))

        return TaskBoardResponse(**board)

    async def get_calendar(
        self,
        user_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        *,
        limit: int = 200,
    ) -> TaskCalendarResponse:
        """Return tasks whose due date falls within ``[start_date, end_date]``."""
        count_stmt = (
            select(func.count(Task.id))
            .where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date >= start_date,
                Task.due_date <= end_date,
            )
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query_stmt = (
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date >= start_date,
                Task.due_date <= end_date,
            )
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.due_date.asc())
            .limit(limit)
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskCalendarResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_today_tasks(
        self, user_id: uuid.UUID, *, limit: int = 50
    ) -> TaskListResponse:
        """Return tasks due today (including overdue) that are not done/archived."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59, microsecond=999999)

        count_stmt = (
            select(func.count(Task.id))
            .where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date <= end_of_day,
                Task.status.notin_({"done", "archived"}),
            )
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query_stmt = (
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date <= end_of_day,
                Task.status.notin_({"done", "archived"}),
            )
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.due_date.asc())
            .limit(limit)
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            offset=0,
            limit=limit,
        )

    async def get_completed_today(
        self, user_id: uuid.UUID, *, limit: int = 50
    ) -> TaskListResponse:
        """Return tasks completed today."""
        now = datetime.now(timezone.utc)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59, microsecond=999999)

        count_stmt = (
            select(func.count(Task.id))
            .where(
                Task.owner_id == user_id,
                Task.completed_at.isnot(None),
                Task.completed_at >= start_of_day,
                Task.completed_at <= end_of_day,
            )
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query_stmt = (
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.completed_at.isnot(None),
                Task.completed_at >= start_of_day,
                Task.completed_at <= end_of_day,
            )
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.completed_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            offset=0,
            limit=limit,
        )

    # ── Stats / Dashboard ─────────────────────────────────────────────

    async def get_task_stats(self, user_id: uuid.UUID) -> TaskStats:
        """Aggregate task statistics for the given user."""
        rows = await self.db.execute(
            select(Task.status, func.count(Task.id)).where(
                Task.owner_id == user_id
            ).group_by(Task.status)
        )
        status_counts: dict[str, int] = dict(rows.all())

        priority_rows = await self.db.execute(
            select(Task.priority, func.count(Task.id)).where(
                Task.owner_id == user_id
            ).group_by(Task.priority)
        )
        priority_counts: dict[str, int] = dict(priority_rows.all())

        now = datetime.now(timezone.utc)

        # Overdue: past due_date and not done/archived
        overdue_result = await self.db.execute(
            select(func.count(Task.id)).where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date < now,
                Task.status.notin_({"done", "archived"}),
            )
        )
        overdue = overdue_result.scalar_one()

        # Incomplete-by-priority (not done/archived)
        incomplete_result = await self.db.execute(
            select(Task.priority, func.count(Task.id)).where(
                Task.owner_id == user_id,
                Task.status.notin_({"done", "archived"}),
            ).group_by(Task.priority)
        )
        incomplete_by_priority: dict[str, int] = dict(incomplete_result.all())

        return TaskStats(
            total=sum(status_counts.values()),
            todo=status_counts.get("todo", 0),
            in_progress=status_counts.get("in_progress", 0),
            review=status_counts.get("review", 0),
            done=status_counts.get("done", 0),
            archived=status_counts.get("archived", 0),
            overdue=overdue,
            critical=priority_counts.get("critical", 0),
            high=priority_counts.get("high", 0),
            medium=priority_counts.get("medium", 0),
            low=priority_counts.get("low", 0),
            incomplete_by_priority=incomplete_by_priority,
        )

    async def get_tasks_by_resource(
        self,
        user_id: uuid.UUID,
        *,
        kb_document_id: uuid.UUID | None = None,
        chat_conversation_id: uuid.UUID | None = None,
        uploaded_document_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> TaskListResponse:
        """Fetch tasks linked to a specific resource (KB doc, chat, or uploaded file)."""
        clauses = [Task.owner_id == user_id]
        if kb_document_id is not None:
            clauses.append(Task.kb_document_id == kb_document_id)
        if chat_conversation_id is not None:
            clauses.append(Task.chat_conversation_id == chat_conversation_id)
        if uploaded_document_id is not None:
            clauses.append(Task.uploaded_document_id == uploaded_document_id)

        # If no filter provided, return empty
        if len(clauses) == 1:
            return TaskListResponse(items=[], total=0, offset=0, limit=limit)

        count_stmt = select(func.count(Task.id)).where(*clauses)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query_stmt = (
            select(Task)
            .where(*clauses)
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            offset=0,
            limit=limit,
        )

    async def get_overdue_tasks(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> TaskListResponse:
        """Fetch tasks that are past their due date and not yet done/archived."""
        now = datetime.now(timezone.utc)
        count_stmt = select(func.count(Task.id)).where(
            Task.owner_id == user_id,
            Task.due_date.isnot(None),
            Task.due_date < now,
            Task.status.notin_({"done", "archived"}),
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        query_stmt = (
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.due_date.isnot(None),
                Task.due_date < now,
                Task.status.notin_({"done", "archived"}),
            )
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
            .order_by(Task.due_date.asc())
            .limit(limit)
        )
        result = await self.db.execute(query_stmt)
        tasks = result.unique().scalars().all()

        return TaskListResponse(
            items=[_to_task_response(t) for t in tasks],
            total=total,
            offset=0,
            limit=limit,
        )
