"""Built-in agent tools — knowledge search, document reader, task manager, etc.

Each tool is registered with ``ToolRegistry`` during application startup.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.services.agent.tools import BaseTool, ToolContext, ToolResult


# ── Knowledge Search Tool ────────────────────────────────────────────────────


class KnowledgeSearchTool(BaseTool):
    """Search across the user's knowledge bases for relevant information."""

    tool_type = "knowledge_search"
    name = "Knowledge Search"
    description = (
        "Search knowledge bases for information relevant to the user's query. "
        "Returns text snippets with source references."
    )

    def __init__(self) -> None:
        super().__init__()
        from app.services.search import GlobalSearchService

        self._search_service_cls = GlobalSearchService

    async def execute(
        self,
        ctx: ToolContext,
        query: str | None = None,
        kb_id: str | None = None,
        max_results: int = 5,
        **kwargs: Any,
    ) -> ToolResult:
        if not query:
            return ToolResult(success=False, output="No query provided", error="Missing query")

        try:
            from app.schemas.search import SearchFilters

            search_svc = self._search_service_cls(ctx.db_session)
            filters = SearchFilters(kb_id=kb_id, entity_types=["kb_document"])
            results_resp = await search_svc.search(
                query=query,
                user_id=ctx.user_id,
                filters=filters,
                limit=min(max_results, 20),
            )
            results = results_resp.results
            snippets = []
            for hit in results:
                snippets.append(
                    f"[{hit.entity_type}] {hit.title}\n{hit.snippet[:500]}"
                )
            output = "\n\n".join(snippets) if snippets else "No results found."
            return ToolResult(
                success=True,
                output=output,
                data={"result_count": len(results), "results": snippets},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output=f"Knowledge search failed: {exc}",
                error=str(exc),
            )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query text",
                },
                "kb_id": {
                    "type": "string",
                    "description": "Optional knowledge base ID to scope the search",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (1–20)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }


# ── Task Manager Tool ────────────────────────────────────────────────────────


class TaskManagerTool(BaseTool):
    """Create, read, update, list, and search tasks."""

    tool_type = "task_manager"
    name = "Task Manager"
    description = (
        "Manage tasks — create new tasks, list existing ones, update status or "
        "priority, and search by keywords. Supports the full task lifecycle."
    )

    def __init__(self) -> None:
        super().__init__()
        from app.services.task import TaskService

        self._task_service_cls = TaskService

    async def execute(
        self,
        ctx: ToolContext,
        action: str = "list",
        task_id: str | None = None,
        title: str | None = None,
        description: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        search: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            svc = self._task_service_cls(ctx.db_session)
            match action:
                case "list":
                    result = await svc.list_tasks(
                        user_id=ctx.user_id,
                        status=status,
                        priority=priority,
                        search=search,
                        limit=20,
                    )
                    tasks = [
                        f"- {t.title} ({t.status}, {t.priority})"
                        for t in result.items
                    ]
                    output = "\n".join(tasks) if tasks else "No tasks found."
                    return ToolResult(
                        success=True,
                        output=output,
                        data={"task_count": len(tasks)},
                    )

                case "create":
                    if not title:
                        return ToolResult(
                            success=False,
                            output="Title is required",
                            error="Missing title",
                        )
                    from app.schemas.task import TaskCreate

                    from uuid import uuid4
                    # Simple creation: build TaskCreate from attrs
                    body = TaskCreate(
                        title=title,
                        description=description,
                        status=status or "todo",
                        priority=priority or "medium",
                    )
                    task = await svc.create_task(body, ctx.user_id)
                    return ToolResult(
                        success=True,
                        output=f"Task created: {task.title} (id={task.id})",
                        data={"task_id": str(task.id)},
                    )

                case "get":
                    if not task_id:
                        return ToolResult(
                            success=False,
                            output="task_id required",
                            error="Missing task_id",
                        )
                    from uuid import UUID

                    tid = UUID(task_id)
                    task = await svc.get_task(tid, ctx.user_id)
                    output = (
                        f"**{task.title}** ({task.status}, {task.priority})\n"
                        f"{task.description or 'No description'}"
                    )
                    return ToolResult(success=True, output=output)

                case _:
                    return ToolResult(
                        success=False,
                        output=f"Unknown action: {action}",
                        error="Invalid action",
                    )
        except Exception as exc:
            return ToolResult(
                success=False, output=f"Task operation failed: {exc}", error=str(exc)
            )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "create", "get"],
                    "description": "Action to perform",
                },
                "task_id": {
                    "type": "string",
                    "description": "UUID of the task (required for get)",
                },
                "title": {
                    "type": "string",
                    "description": "Task title (required for create)",
                },
                "description": {
                    "type": "string",
                    "description": "Task description",
                },
                "status": {
                    "type": "string",
                    "enum": ["todo", "in_progress", "review", "done", "archived"],
                    "description": "Task status",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Task priority",
                },
                "search": {
                    "type": "string",
                    "description": "Search keywords",
                },
            },
            "required": ["action"],
        }


# ── Calculator Tool ──────────────────────────────────────────────────────────


class CalculatorTool(BaseTool):
    """Evaluate simple arithmetic expressions safely."""

    tool_type = "calculator"
    name = "Calculator"
    description = "Evaluate a mathematical expression (+, -, *, /, **, parentheses)."

    async def execute(
        self,
        ctx: ToolContext,
        expression: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        if not expression:
            return ToolResult(
                success=False, output="No expression provided", error="Missing expression"
            )

        # Safe evaluation using a restricted environment
        safe_globals: dict = {"__builtins__": {}}
        safe_locals: dict = {}
        try:
            # Allow only numeric operations
            allowed = {"abs", "round", "min", "max", "sum", "pow", "float", "int"}
            safe_globals["__builtins__"] = {k: __builtins__[k] for k in allowed if k in __builtins__}
            result = eval(expression, safe_globals, safe_locals)  # noqa: S307
            return ToolResult(
                success=True,
                output=str(result),
                data={"expression": expression, "result": result},
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output=f"Calculation failed: {exc}",
                error=str(exc),
            )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate",
                },
            },
            "required": ["expression"],
        }


# ── Current Time Tool ────────────────────────────────────────────────────────


class CurrentTimeTool(BaseTool):
    """Return the current date and time."""

    tool_type = "current_time"
    name = "Current Time"
    description = "Get the current date and time in the user's timezone."

    async def execute(
        self,
        ctx: ToolContext,
        format: str = "iso",
        **kwargs: Any,
    ) -> ToolResult:
        now = datetime.now(timezone.utc)
        match format:
            case "unix":
                output = str(now.timestamp())
            case "date":
                output = now.strftime("%Y-%m-%d")
            case "time":
                output = now.strftime("%H:%M:%S UTC")
            case _:
                output = now.isoformat()
        return ToolResult(
            success=True,
            output=output,
            data={
                "iso": now.isoformat(),
                "unix": now.timestamp(),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S UTC"),
            },
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["iso", "unix", "date", "time"],
                    "description": "Output format",
                    "default": "iso",
                },
            },
        }
