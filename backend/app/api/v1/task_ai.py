"""AI-powered Task Assistant API router.

Provides endpoints for all AI Task Assistant features: natural-language
task generation, subtask suggestions, effort estimation, priority/due-date
recommendations, work summaries, chat-to-task and document-to-task conversion,
and next-action generation.

All endpoints are ownership-gated via the ``get_current_active_user``
dependency and reuse the existing ``AIProvider`` abstraction.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_active_user
from app.models.user import User
from app.schemas.task_ai import (
    AIConvertChatRequest,
    AIConvertChatResponse,
    AIConvertDocumentRequest,
    AIConvertDocumentResponse,
    AIEffortEstimateResponse,
    AINextActionsResponse,
    AIPrioritySuggestionResponse,
    AISubtaskRequest,
    AISubtaskResponse,
    AISummaryRequest,
    AISummaryResponse,
    AITaskGenerationRequest,
    AITaskGenerationResponse,
)
from app.services.task import TaskNotFound
from app.services.task.ai_assistant import TaskAIAssistant

router = APIRouter()


@router.post(
    "/ai/tasks/generate",
    response_model=AITaskGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate tasks from natural language",
    description=(
        "Parse unstructured text and return structured task suggestions "
        "with title, description, priority, estimated effort, due date, "
        "and labels."
    ),
)
async def generate_tasks(
    body: AITaskGenerationRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AITaskGenerationResponse:
    """Generate task suggestions from natural language input."""
    assistant = TaskAIAssistant(db)
    return await assistant.generate_tasks_from_text(
        text=body.text,
        user_id=current_user.id,
        context=body.context,
    )


@router.post(
    "/ai/tasks/subtasks",
    response_model=AISubtaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate subtasks",
    description=(
        "Suggest subtasks that break down an existing task into "
        "manageable pieces. Optionally specify the desired number of subtasks."
    ),
)
async def generate_subtasks(
    body: AISubtaskRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AISubtaskResponse:
    """Generate subtask suggestions for a task."""
    assistant = TaskAIAssistant(db)
    try:
        return await assistant.generate_subtasks(
            task_id=body.task_id,
            user_id=current_user.id,
            count=body.count,
        )
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/ai/tasks/{task_id}/estimate",
    response_model=AIEffortEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Estimate task effort",
    description=(
        "Use AI to estimate how long a task will take to complete, "
        "returning estimated minutes, confidence level, and reasoning."
    ),
)
async def estimate_effort(
    task_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AIEffortEstimateResponse:
    """Estimate effort for a task using AI."""
    assistant = TaskAIAssistant(db)
    try:
        return await assistant.estimate_effort(
            task_id=task_id,
            user_id=current_user.id,
        )
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/ai/tasks/{task_id}/suggest-priority",
    response_model=AIPrioritySuggestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Suggest priority and due date",
    description=(
        "Use AI to suggest the appropriate priority level and optional "
        "due date for a task based on its content."
    ),
)
async def suggest_priority(
    task_id: UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AIPrioritySuggestionResponse:
    """Suggest priority and due date for a task."""
    assistant = TaskAIAssistant(db)
    try:
        return await assistant.suggest_priority_due_date(
            task_id=task_id,
            user_id=current_user.id,
        )
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )


@router.post(
    "/ai/tasks/summary",
    response_model=AISummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Summarise completed work",
    description=(
        "Generate a markdown summary of tasks completed within a "
        "specified date range. Defaults to the current week."
    ),
)
async def summarize_work(
    body: AISummaryRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AISummaryResponse:
    """Summarise completed work in a date range."""
    assistant = TaskAIAssistant(db)
    return await assistant.summarize_completed_work(
        user_id=current_user.id,
        start_date=body.start_date,
        end_date=body.end_date,
    )


@router.post(
    "/ai/tasks/convert-chat",
    response_model=AIConvertChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert chat to task",
    description=(
        "Extract a task suggestion from an AI chat conversation, "
        "returning a task draft and key action points."
    ),
)
async def convert_chat_to_task(
    body: AIConvertChatRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AIConvertChatResponse:
    """Convert a chat conversation into a task suggestion."""
    assistant = TaskAIAssistant(db)
    try:
        return await assistant.convert_chat_to_task(
            conversation_id=body.conversation_id,
            user_id=current_user.id,
        )
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )


@router.post(
    "/ai/tasks/convert-document",
    response_model=AIConvertDocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert document to task",
    description=(
        "Extract a task suggestion from a knowledge-base document, "
        "returning a task draft and key action points."
    ),
)
async def convert_document_to_task(
    body: AIConvertDocumentRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AIConvertDocumentResponse:
    """Convert a knowledge-base document into a task suggestion."""
    assistant = TaskAIAssistant(db)
    try:
        return await assistant.convert_document_to_task(
            document_id=body.document_id,
            user_id=current_user.id,
        )
    except TaskNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )


@router.get(
    "/ai/tasks/next-actions",
    response_model=AINextActionsResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate next actions",
    description=(
        "Suggest the most important next actions based on the user's "
        "current incomplete tasks, prioritised by urgency and importance."
    ),
)
async def get_next_actions(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AINextActionsResponse:
    """Generate next-action suggestions based on current task state."""
    assistant = TaskAIAssistant(db)
    return await assistant.generate_next_actions(user_id=current_user.id)
