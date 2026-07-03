"""Task management API router.

Provides full CRUD endpoints for tasks, plus sub-resource endpoints for
labels, comments, and attachments.  All endpoints are ownership-gated
via the ``get_current_active_user`` dependency.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, get_current_active_user
from app.models.user import User
from app.schemas.task import (
    TaskBoardResponse,
    TaskCalendarResponse,
    TaskCommentCreate,
    TaskCreate,
    TaskLabelSchema,
    TaskListResponse,
    TaskResponse,
    TaskStats,
    TaskUpdate,
)
from app.services.task import (
    AttachmentNotFound,
    CommentNotFound,
    LabelNotFound,
    TaskNotFound,
    TaskService,
)

router = APIRouter()


# ── Task CRUD ──────────────────────────────────────────────────────────────────


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description=(
        "Create a new task owned by the current user.  All fields "
        "from the ``TaskCreate`` schema are accepted.  Status defaults "
        "to ``todo`` and priority to ``medium``."
    ),
)
async def create_task(
    body: TaskCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Create a new task."""
    service = TaskService(db)
    return await service.create_task(body, current_user.id)


@router.get(
    "/tasks",
    response_model=TaskListResponse,
    summary="List tasks",
    description=(
        "Return a paginated, filterable list of tasks owned by the "
        "current user.  Supports filtering by status, priority, and "
        "full-text search on title/description."
    ),
)
async def list_tasks(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    status: str | None = Query(None, description="Filter by status"),
    priority: str | None = Query(None, description="Filter by priority"),
    search: str | None = Query(
        None, min_length=1, description="Search in title and description"
    ),
    offset: int = Query(
        0, ge=0, le=1000, description="Number of records to skip (max 1000)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> TaskListResponse:
    """List tasks with optional filtering and pagination."""
    service = TaskService(db)
    return await service.list_tasks(
        current_user.id,
        status=status,
        priority=priority,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/tasks/search",
    response_model=TaskListResponse,
    summary="Search tasks",
    description=(
        "Full-text-like search across task title and description. "
        "Convenience alias for ``GET /tasks?search=...``."
    ),
)
async def search_tasks(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    q: str = Query(..., min_length=1, description="Search query"),
    offset: int = Query(
        0, ge=0, le=1000, description="Number of records to skip (max 1000)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> TaskListResponse:
    """Search tasks by title or description."""
    service = TaskService(db)
    return await service.search_tasks(
        current_user.id, q, offset=offset, limit=limit
    )


@router.get(
    "/tasks/board",
    response_model=TaskBoardResponse,
    summary="Kanban board",
    description=(
        "Return all tasks grouped by their status column for the "
        "Kanban board view.  Owned by the current user."
    ),
)
async def get_task_board(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(
        200, ge=1, le=500, description="Maximum tasks per column"
    ),
) -> TaskBoardResponse:
    """Get tasks grouped by status."""
    service = TaskService(db)
    return await service.get_board(current_user.id, limit=limit)


@router.get(
    "/tasks/calendar",
    response_model=TaskCalendarResponse,
    summary="Calendar view",
    description=(
        "Return tasks whose due date falls within the given date "
        "range (ISO 8601).  Defaults to the current month if no "
        "dates are provided."
    ),
)
async def get_task_calendar(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    start_date: str | None = Query(
        None, description="Start of date range (ISO 8601)"
    ),
    end_date: str | None = Query(
        None, description="End of date range (ISO 8601)"
    ),
    limit: int = Query(
        200, ge=1, le=500, description="Maximum records to return"
    ),
) -> TaskCalendarResponse:
    """Get tasks with due dates in a range."""
    now = datetime.now(timezone.utc)
    if start_date:
        parsed_start = datetime.fromisoformat(start_date)
    else:
        # Default to start of current month
        parsed_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        parsed_end = datetime.fromisoformat(end_date)
    else:
        # Default to end of current month
        last_day = calendar.monthrange(now.year, now.month)[1]
        parsed_end = now.replace(day=last_day, hour=23, minute=59, second=59, microsecond=999999)

    service = TaskService(db)
    return await service.get_calendar(
        current_user.id, parsed_start, parsed_end, limit=limit
    )

@router.get(
    "/tasks/stats",
    response_model=TaskStats,
    summary="Task stats",
    description="Return aggregate task statistics for the current user.",
)
async def get_task_stats(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskStats:
    """Get task stats for the current user."""
    service = TaskService(db)
    return await service.get_task_stats(current_user.id)


@router.get(
    "/tasks/by-resource",
    response_model=TaskListResponse,
    summary="Tasks by resource",
    description=(
        "Return tasks linked to a given resource — a KB document, "
        "chat conversation, or uploaded file.  At least one of "
        "``kb_document_id``, ``chat_conversation_id``, or "
        "``uploaded_document_id`` must be provided."
    ),
)
async def list_tasks_by_resource(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    kb_document_id: uuid.UUID | None = Query(
        None, description="Filter by knowledge base document ID"
    ),
    chat_conversation_id: uuid.UUID | None = Query(
        None, description="Filter by chat conversation ID"
    ),
    uploaded_document_id: uuid.UUID | None = Query(
        None, description="Filter by uploaded file/document ID"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> TaskListResponse:
    """List tasks linked to a resource."""
    service = TaskService(db)
    return await service.get_tasks_by_resource(
        current_user.id,
        kb_document_id=kb_document_id,
        chat_conversation_id=chat_conversation_id,
        uploaded_document_id=uploaded_document_id,
        limit=limit,
    )


@router.get(
    "/tasks/overdue",
    response_model=TaskListResponse,
    summary="Overdue tasks",
    description=(
        "Return tasks past their due date that are not yet done or "
        "archived, ordered by due-date ascending."
    ),
)
async def get_overdue_tasks(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> TaskListResponse:
    """Get overdue tasks for the current user."""
    service = TaskService(db)
    return await service.get_overdue_tasks(current_user.id, limit=limit)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get task",
    description=(
        "Return a single task with all nested relations (labels, "
        "comments, attachments).  Ownership-gated — returns 404 "
        "for another user's task."
    ),
)
async def get_task(
    task_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Get a single task by ID."""
    service = TaskService(db)
    try:
        return await service.get_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.patch(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update task",
    description=(
        "Partial update of a task.  Only the fields provided in the "
        "request body are changed.  Ownership-gated — returns 404 for "
        "another user's task."
    ),
)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Update a task (partial update)."""
    service = TaskService(db)
    try:
        return await service.update_task(task_id, body, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete task",
    description=(
        "Delete a task and all its child records (comments, labels, "
        "attachments cascade).  Ownership-gated — returns 404 for "
        "another user's task."
    ),
)
async def delete_task(
    task_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a task."""
    service = TaskService(db)
    try:
        await service.delete_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


# ── Status transitions ─────────────────────────────────────────────────────────


@router.post(
    "/tasks/{task_id}/complete",
    response_model=TaskResponse,
    summary="Complete task",
    description=(
        "Mark a task as done.  Idempotent — completing an already-done "
        "task is a no-op.  Ownership-gated."
    ),
)
async def complete_task(
    task_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Mark a task as complete."""
    service = TaskService(db)
    try:
        return await service.complete_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/tasks/{task_id}/archive",
    response_model=TaskResponse,
    summary="Archive task",
    description=(
        "Archive a task (moves it to the ``archived`` status). "
        "Ownership-gated — returns 404 for another user's task."
    ),
)
async def archive_task(
    task_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Archive a task."""
    service = TaskService(db)
    try:
        return await service.archive_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/tasks/{task_id}/restore",
    response_model=TaskResponse,
    summary="Restore task",
    description=(
        "Restore an archived task back to ``todo`` status. "
        "No-op if the task is not archived.  Ownership-gated."
    ),
)
async def restore_task(
    task_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Restore an archived task."""
    service = TaskService(db)
    try:
        return await service.restore_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


# ── Labels ─────────────────────────────────────────────────────────────────────


@router.post(
    "/tasks/{task_id}/labels",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Add label",
    description="Add a label to a task.  Accepts ``name`` (required) "
    "and ``color`` (optional hex code) in the request body.",
)
async def add_label(
    task_id: uuid.UUID,
    body: TaskLabelSchema,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Add a label to a task."""
    service = TaskService(db)
    try:
        label = await service.add_label(
            task_id, current_user.id, body.name, body.color
        )
        return {"id": str(label.id), "name": label.name, "color": label.color}
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove label",
    description="Remove a label from a task.",
)
async def remove_label(
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove a label from a task."""
    service = TaskService(db)
    try:
        await service.remove_label(task_id, current_user.id, label_id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


# ── Comments ────────────────────────────────────────────────────────────────────


@router.post(
    "/tasks/{task_id}/comments",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add comment",
    description="Add a comment to a task.  Returns the updated task.",
)
async def add_comment(
    task_id: uuid.UUID,
    body: TaskCommentCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Add a comment to a task."""
    service = TaskService(db)
    try:
        await service.add_comment(task_id, current_user.id, body)
        return await service.get_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.patch(
    "/tasks/{task_id}/comments/{comment_id}",
    response_model=TaskResponse,
    summary="Update comment",
    description=(
        "Update the content of a comment.  Only the comment author "
        "may update.  Returns the updated task."
    ),
)
async def update_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: dict,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Update a comment's content."""
    content = body.get("content", "")
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content is required",
        )
    service = TaskService(db)
    try:
        await service.update_comment(
            task_id, current_user.id, comment_id, content
        )
        return await service.get_task(task_id, current_user.id)
    except (TaskNotFound, CommentNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )


@router.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description=(
        "Delete a comment.  Only the comment author or task owner "
        "may delete."
    ),
)
async def delete_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a comment."""
    service = TaskService(db)
    try:
        await service.delete_comment(task_id, current_user.id, comment_id)
    except (TaskNotFound, CommentNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )


# ── Attachments ────────────────────────────────────────────────────────────────


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add attachment",
    description=(
        "Attach a file to a task.  The file must already be uploaded "
        "(use the Storage API first).  Provide the file's UUID in the "
        "request body.  Returns the updated task."
    ),
)
async def add_attachment(
    task_id: uuid.UUID,
    body: dict,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> TaskResponse:
    """Attach an existing uploaded file to a task."""
    file_id = body.get("file_id")
    if not file_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_id is required",
        )
    try:
        file_id_uuid = uuid.UUID(str(file_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file_id format",
        )

    service = TaskService(db)
    try:
        await service.add_attachment(
            task_id, current_user.id, file_id_uuid
        )
        return await service.get_task(task_id, current_user.id)
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.delete(
    "/tasks/{task_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove attachment",
    description="Remove an attachment from a task.",
)
async def remove_attachment(
    task_id: uuid.UUID,
    attachment_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove an attachment from a task."""
    service = TaskService(db)
    try:
        await service.remove_attachment(
            task_id, current_user.id, attachment_id
        )
    except (TaskNotFound, AttachmentNotFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attachment not found",
        )
