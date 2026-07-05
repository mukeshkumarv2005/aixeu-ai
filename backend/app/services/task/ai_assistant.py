"""AI-powered Task Assistant service.

Leverages the existing ``AIProvider`` abstraction to provide natural-language
task management features: task extraction from text, subtask generation,
effort estimation, priority/due-date suggestions, work summaries,
chat-to-task and document-to-task conversion, and next-action generation.

All methods are ownership-gated — callers must pass the authenticated
user's ID.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.conversation import Conversation, Message
from app.models.knowledge import KnowledgeBase, KnowledgeBaseDocument
from app.models.task import Task
from app.schemas.task_ai import (
    AIConvertChatResponse,
    AIConvertDocumentResponse,
    AIEffortEstimateResponse,
    AINextActionItem,
    AINextActionsResponse,
    AIPrioritySuggestionResponse,
    AISubtaskItem,
    AISubtaskResponse,
    AISummaryResponse,
    AITaskDraft,
    AITaskGenerationResponse,
)
from app.services.ai import AIProvider, ChatMessage, get_ai_provider
from app.services.task import TaskNotFound, TaskService


# ── Helpers ────────────────────────────────────────────────────────────────────


def _now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _week_boundary() -> tuple[datetime, datetime]:
    """Return (start_of_week, now) for the current week (Mon–Sun)."""
    now = _now()
    start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Walk back to Monday
    days_since_monday = start.weekday()  # Monday=0
    start = start - timedelta(days=days_since_monday)
    return start, now


async def _collect_ai_response(
    ai: AIProvider,
    messages: list[ChatMessage],
    model: str | None = None,
) -> str:
    """Send messages to the AI provider and collect the full streaming response."""
    parts: list[str] = []
    async for event in ai.stream_chat(messages, model=model):
        if event.content:
            parts.append(event.content)
    return "".join(parts)


def _extract_json(text: str) -> dict[str, Any] | list[Any] | None:
    """Try to extract a JSON object or array from a string.

    Attempts to parse directly first, then looks for a JSON block
    delimited by `````json```` or ````` `` ``` markers.
    """
    # Try direct parse
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` block
    json_block = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
    )
    if json_block:
        try:
            return json.loads(json_block.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try extracting the first { ... } or [ ... ] block
    for char in ("{", "["):
        start = text.find(char)
        if start == -1:
            continue
        end_char = "}" if char == "{" else "]"
        depth = 0
        for i in range(start, len(text)):
            if text[i] == char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _safe_json_extract(
    text: str, default: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Extract a JSON dict from AI output, returning ``default`` on failure."""
    result = _extract_json(text)
    if isinstance(result, dict):
        return result
    return default or {}


def _build_task_messages_for_ai(task: Task) -> list[ChatMessage]:
    """Build a ChatMessage list describing a task for AI prompts."""
    lines = [
        f"Title: {task.title}",
        f"Status: {task.status}",
        f"Priority: {task.priority}",
    ]
    if task.description:
        lines.append(f"Description: {task.description}")
    if task.due_date:
        lines.append(f"Due: {task.due_date.isoformat()}")
    if task.estimated_minutes:
        lines.append(f"Estimated: {task.estimated_minutes} min")
    return [ChatMessage(role="user", content="\n".join(lines))]


# ── System prompts ─────────────────────────────────────────────────────────────

SYSTEM_GENERATE_TASKS = (
    "You are an AI task management assistant. Extract actionable tasks from "
    "the user's natural language input. For each task, provide a clear title, "
    "optional description, priority (low/medium/high/critical), estimated "
    "minutes, optional due date (ISO 8601), and relevant labels (as strings). "
    "Respond with a JSON object matching exactly this structure:\n"
    '{"tasks": [{"title": "...", "description": "...", "priority": "medium", '
    '"estimated_minutes": null, "due_date": null, "labels": []}]}\n'
    "Only output valid JSON — no commentary, no markdown formatting."
)

SYSTEM_GENERATE_SUBTASKS = (
    "You are an AI project planner. Given a task, suggest logical subtasks "
    "that break it down into manageable pieces. For each subtask, provide a "
    "title, optional description, and estimated minutes. "
    "Respond with a JSON object:\n"
    '{"subtasks": [{"title": "...", "description": null, '
    '"estimated_minutes": null}]}\n'
    "Only output valid JSON — no commentary."
)

SYSTEM_ESTIMATE_EFFORT = (
    "You are an AI effort estimator. Given a task, estimate how long it "
    "will take to complete in minutes. Provide a confidence level "
    "(high/medium/low) and a brief reasoning. "
    "Respond with a JSON object:\n"
    '{"estimated_minutes": 60, "confidence": "medium", '
    '"reasoning": "..."}\n'
    "Only output valid JSON — no commentary."
)

SYSTEM_SUGGEST_PRIORITY = (
    "You are an AI prioritisation assistant. Given a task, suggest the "
    "appropriate priority level (low/medium/high/critical) and an optional "
    "due date. Consider typical urgency signals in the task content. "
    "Respond with a JSON object:\n"
    '{"priority": "medium", "due_date": null, "reasoning": "..."}\n'
    "due_date must be ISO 8601 or null. Only output valid JSON."
)

SYSTEM_SUMMARIZE_WORK = (
    "You are an AI productivity reporter. Given a list of recently completed "
    "tasks, write a concise markdown summary of what was accomplished. "
    "Identify key highlights and patterns. "
    "Respond with a JSON object:\n"
    '{"summary": "markdown text...", "total_completed": 0, '
    '"highlights": ["..."]}\n'
    "Only output valid JSON — no commentary."
)

SYSTEM_CHAT_TO_TASK = (
    "You are an AI that extracts action items from chat conversations. "
    "Given a conversation transcript, identify the single most important "
    "actionable task. Provide a title, description, priority, and key "
    "discussion points. "
    "Respond with a JSON object:\n"
    '{"task": {"title": "...", "description": "...", "priority": "medium", '
    '"estimated_minutes": null, "due_date": null, "labels": []}, '
    '"key_points": ["..."]}\n'
    "Only output valid JSON — no commentary."
)

SYSTEM_DOCUMENT_TO_TASK = (
    "You are an AI that extracts action items from documents. "
    "Given a document's content, identify the single most important "
    "actionable task it implies. Provide a title, description, priority, "
    "and key points from the document. "
    "Respond with a JSON object:\n"
    '{"task": {"title": "...", "description": "...", "priority": "medium", '
    '"estimated_minutes": null, "due_date": null, "labels": []}, '
    '"key_points": ["..."]}\n'
    "Only output valid JSON — no commentary."
)

SYSTEM_NEXT_ACTIONS = (
    "You are an AI productivity coach. Given the user's current incomplete "
    "tasks (sorted by priority and due date), suggest the most important "
    "next actions. Focus on high-impact, time-sensitive items. "
    "Respond with a JSON object:\n"
    '{"actions": [{"title": "...", "context": "...", '
    '"source_task_id": null, "priority": "medium"}], '
    '"summary": "..."}\n'
    "Only output valid JSON — no commentary."
)


# ── Service ────────────────────────────────────────────────────────────────────


class TaskAIAssistant:
    """AI-powered operations on user tasks.

    Every method that touches task data is ownership-gated and will raise
    ``TaskNotFound`` (404) if the caller does not own the referenced task.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ai: AIProvider = get_ai_provider()
        self._task_service = TaskService(db)

    # ── Internal helpers ───────────────────────────────────────────────

    async def _call_ai(
        self,
        system_prompt: str,
        user_message: str,
        model: str | None = None,
    ) -> str:
        """Send a system+user message pair to the AI and collect the response."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_message),
        ]
        return await _collect_ai_response(self.ai, messages, model=model)

    async def _get_task_or_raise(
        self, task_id: uuid.UUID, user_id: uuid.UUID
    ) -> Task:
        """Fetch a task, raising 404 if not found / not owned."""
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id, Task.owner_id == user_id)
            .options(
                joinedload(Task.labels),
                joinedload(Task.comments),
                joinedload(Task.attachments),
            )
        )
        task = result.unique().scalar_one_or_none()
        if task is None:
            raise TaskNotFound(task_id)
        return task

    # ── 1. Generate tasks from natural language ─────────────────────────

    async def generate_tasks_from_text(
        self,
        text: str,
        user_id: uuid.UUID,
        context: str | None = None,
    ) -> AITaskGenerationResponse:
        """Parse natural language and return structured task suggestions."""
        message = text
        if context:
            message = f"Context:\n{context}\n\nText:\n{text}"

        response_text = await self._call_ai(SYSTEM_GENERATE_TASKS, message)
        data = _safe_json_extract(response_text, {"tasks": []})

        tasks_raw = data.get("tasks", [])
        tasks = []
        for t in tasks_raw:
            tasks.append(
                AITaskDraft(
                    title=t.get("title", "Untitled task"),
                    description=t.get("description"),
                    priority=t.get("priority", "medium"),
                    estimated_minutes=t.get("estimated_minutes"),
                    due_date=self._parse_datetime(t.get("due_date")),
                    labels=t.get("labels", []),
                )
            )

        return AITaskGenerationResponse(tasks=tasks)

    # ── 2. Generate subtasks ────────────────────────────────────────────

    async def generate_subtasks(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
        count: int | None = None,
    ) -> AISubtaskResponse:
        """Suggest subtasks that break down an existing task."""
        task = await self._get_task_or_raise(task_id, user_id)
        msg_parts = [
            f"Title: {task.title}",
        ]
        if task.description:
            msg_parts.append(f"Description: {task.description}")
        msg_parts.append(f"Priority: {task.priority}")
        if task.estimated_minutes:
            msg_parts.append(f"Estimated effort: {task.estimated_minutes} min")
        if count:
            msg_parts.append(f"\nSuggest approximately {count} subtasks.")

        response_text = await self._call_ai(
            SYSTEM_GENERATE_SUBTASKS, "\n".join(msg_parts)
        )
        data = _safe_json_extract(response_text, {"subtasks": []})

        subtasks_raw = data.get("subtasks", [])
        subtasks = [
            AISubtaskItem(
                title=s.get("title", "Untitled subtask"),
                description=s.get("description"),
                estimated_minutes=s.get("estimated_minutes"),
            )
            for s in subtasks_raw
        ]

        return AISubtaskResponse(subtasks=subtasks)

    # ── 3. Estimate effort ──────────────────────────────────────────────

    async def estimate_effort(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIEffortEstimateResponse:
        """Estimate effort in minutes for a given task."""
        task = await self._get_task_or_raise(task_id, user_id)
        response_text = await self._call_ai(
            SYSTEM_ESTIMATE_EFFORT,
            f"Title: {task.title}\n"
            f"Description: {task.description or '(no description)'}\n"
            f"Priority: {task.priority}",
        )
        data = _safe_json_extract(
            response_text,
            {"estimated_minutes": 60, "confidence": "low", "reasoning": None},
        )

        return AIEffortEstimateResponse(
            estimated_minutes=max(
                1, data.get("estimated_minutes", 60)
            ),
            confidence=data.get("confidence", "low"),
            reasoning=data.get("reasoning"),
        )

    # ── 4. Suggest priority and due date ────────────────────────────────

    async def suggest_priority_due_date(
        self,
        task_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIPrioritySuggestionResponse:
        """Suggest priority level and optional due date for a task."""
        task = await self._get_task_or_raise(task_id, user_id)
        response_text = await self._call_ai(
            SYSTEM_SUGGEST_PRIORITY,
            f"Title: {task.title}\n"
            f"Description: {task.description or '(no description)'}\n"
            f"Current priority: {task.priority}\n"
            f"Due: {task.due_date.isoformat() if task.due_date else 'not set'}",
        )
        data = _safe_json_extract(
            response_text,
            {"priority": "medium", "due_date": None, "reasoning": None},
        )

        return AIPrioritySuggestionResponse(
            priority=data.get("priority", "medium"),
            due_date=self._parse_datetime(data.get("due_date")),
            reasoning=data.get("reasoning"),
        )

    # ── 5. Summarise completed work ─────────────────────────────────────

    async def summarize_completed_work(
        self,
        user_id: uuid.UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AISummaryResponse:
        """Summarise tasks completed within a date range."""
        if end_date is None:
            end_date = _now()
        if start_date is None:
            start_date, _ = _week_boundary()

        # Fetch completed tasks in range
        result = await self.db.execute(
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.status == "done",
                Task.completed_at.isnot(None),
                Task.completed_at >= start_date,
                Task.completed_at <= end_date,
            )
            .order_by(Task.completed_at.desc())
            .limit(100)
        )
        completed_tasks = result.unique().scalars().all()

        if not completed_tasks:
            return AISummaryResponse(
                summary="No tasks were completed in this period.",
                total_completed=0,
                highlights=[],
            )

        # Build a summary for the AI
        task_lines = []
        for t in completed_tasks:
            line = (
                f"- [{t.priority}] {t.title}"
                f"{' — ' + t.description[:120] if t.description else ''}"
                f" (completed: {t.completed_at.strftime('%Y-%m-%d') if t.completed_at else '?'})"
            )
            task_lines.append(line)

        user_message = (
            f"Tasks completed between "
            f"{start_date.strftime('%Y-%m-%d')} and "
            f"{end_date.strftime('%Y-%m-%d')}:\n\n"
            + "\n".join(task_lines)
        )

        response_text = await self._call_ai(SYSTEM_SUMMARIZE_WORK, user_message)
        data = _safe_json_extract(
            response_text,
            {
                "summary": "Completed {} tasks.".format(len(completed_tasks)),
                "total_completed": len(completed_tasks),
                "highlights": [],
            },
        )

        return AISummaryResponse(
            summary=data.get("summary", ""),
            total_completed=data.get("total_completed", len(completed_tasks)),
            highlights=data.get("highlights", []),
        )

    # ── 6. Convert chat to task ─────────────────────────────────────────

    async def convert_chat_to_task(
        self,
        conversation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIConvertChatResponse:
        """Extract a task suggestion from a chat conversation."""
        # Fetch conversation with messages
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .options(joinedload(Conversation.messages))
        )
        conversation = result.unique().scalar_one_or_none()
        if conversation is None:
            raise TaskNotFound(conversation_id)  # Treat as not-found

        # Build transcript
        transcript_parts = []
        for msg in conversation.messages:
            transcript_parts.append(f"{msg.role}: {msg.content[:2000]}")
        transcript = "\n".join(transcript_parts)

        response_text = await self._call_ai(
            SYSTEM_CHAT_TO_TASK,
            f"Conversation title: {conversation.title or 'Untitled'}\n\n"
            f"Transcript:\n{transcript[:15000]}",
        )
        data = _safe_json_extract(
            response_text,
            {
                "task": {
                    "title": "Task from chat",
                    "description": None,
                    "priority": "medium",
                    "estimated_minutes": None,
                    "due_date": None,
                    "labels": [],
                },
                "key_points": [],
            },
        )

        task_data = data.get("task", {})
        return AIConvertChatResponse(
            task=AITaskDraft(
                title=task_data.get("title", "Task from chat"),
                description=task_data.get("description"),
                priority=task_data.get("priority", "medium"),
                estimated_minutes=task_data.get("estimated_minutes"),
                due_date=self._parse_datetime(task_data.get("due_date")),
                labels=task_data.get("labels", []),
            ),
            key_points=data.get("key_points", []),
        )

    # ── 7. Convert document to task ─────────────────────────────────────

    async def convert_document_to_task(
        self,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AIConvertDocumentResponse:
        """Extract a task suggestion from a knowledge-base document."""
        result = await self.db.execute(
            select(KnowledgeBaseDocument)
            .join(KnowledgeBase, KnowledgeBaseDocument.knowledge_base_id == KnowledgeBase.id)
            .where(
                KnowledgeBaseDocument.id == document_id,
                KnowledgeBase.user_id == user_id,
            )
        )
        doc = result.unique().scalar_one_or_none()
        if doc is None:
            raise TaskNotFound(document_id)

        response_text = await self._call_ai(
            SYSTEM_DOCUMENT_TO_TASK,
            f"Document title: {doc.title}\n\n"
            f"Content:\n{doc.content[:15000]}",
        )
        data = _safe_json_extract(
            response_text,
            {
                "task": {
                    "title": "Task from document",
                    "description": None,
                    "priority": "medium",
                    "estimated_minutes": None,
                    "due_date": None,
                    "labels": [],
                },
                "key_points": [],
            },
        )

        task_data = data.get("task", {})
        return AIConvertDocumentResponse(
            task=AITaskDraft(
                title=task_data.get("title", "Task from document"),
                description=task_data.get("description"),
                priority=task_data.get("priority", "medium"),
                estimated_minutes=task_data.get("estimated_minutes"),
                due_date=self._parse_datetime(task_data.get("due_date")),
                labels=task_data.get("labels", []),
            ),
            key_points=data.get("key_points", []),
        )

    # ── 8. Generate next actions ────────────────────────────────────────

    async def generate_next_actions(
        self,
        user_id: uuid.UUID,
    ) -> AINextActionsResponse:
        """Suggest next actions based on current incomplete tasks."""
        # Fetch incomplete tasks ordered by priority then due date
        result = await self.db.execute(
            select(Task)
            .where(
                Task.owner_id == user_id,
                Task.status.notin_({"done", "archived"}),
            )
            .order_by(
                # Custom priority ordering via case statement
                Task.priority.desc(),
                Task.due_date.asc().nulls_last(),
            )
            .limit(20)
        )
        tasks = result.unique().scalars().all()

        if not tasks:
            return AINextActionsResponse(
                actions=[], summary="No pending tasks to suggest next actions for."
            )

        task_list = []
        for t in tasks:
            due = t.due_date.strftime("%Y-%m-%d") if t.due_date else "no due date"
            task_list.append(
                f"- [ID:{t.id}] {t.title} ({t.priority}, due: {due})"
                f"{' — ' + t.description[:100] if t.description else ''}"
            )

        user_message = (
            "Current incomplete tasks (sorted by priority, then due date):\n\n"
            + "\n".join(task_list)
        )

        response_text = await self._call_ai(SYSTEM_NEXT_ACTIONS, user_message)
        data = _safe_json_extract(
            response_text,
            {"actions": [], "summary": None},
        )

        actions_raw = data.get("actions", [])
        actions = []
        for a in actions_raw:
            source_id = a.get("source_task_id")
            parsed_id: uuid.UUID | None = None
            if source_id:
                try:
                    parsed_id = uuid.UUID(str(source_id))
                except (ValueError, AttributeError):
                    pass
            actions.append(
                AINextActionItem(
                    title=a.get("title", "Next action"),
                    context=a.get("context"),
                    source_task_id=parsed_id,
                    priority=a.get("priority", "medium"),
                )
            )

        return AINextActionsResponse(
            actions=actions,
            summary=data.get("summary"),
        )

    # ── Date parsing helper ─────────────────────────────────────────────

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        """Try to parse a datetime from various formats the AI might return."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # Try ISO 8601
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                pass
            # Try date-only (YYYY-MM-DD)
            try:
                from datetime import date

                parsed = date.fromisoformat(value[:10])
                return datetime(
                    parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                pass
        return None
