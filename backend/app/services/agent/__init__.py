"""Agent service — CRUD, run execution, tool and template management.

The ``AgentService`` is the main orchestrator for the AI Agent framework.
It follows the same service-layer pattern as ``TaskService``:
- Class takes ``AsyncSession``
- Raises ``AppException`` subclasses for 4xx errors
- Uses helpers for fetch-or-raise patterns
- Returns Pydantic response objects
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import AppException
from app.models.agent import Agent, AgentRun, AgentTemplate, AgentTool
from app.schemas.agent import (
    AGENT_STATUSES,
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentRunExecuteRequest,
    AgentRunExecuteResponse,
    AgentRunListResponse,
    AgentRunResponse,
    AgentToolCreate,
    AgentToolResponse,
    AgentUpdate,
    AgentTemplateCreate,
    AgentTemplateListResponse,
    AgentTemplateResponse,
    AgentTemplateUpdate,
)
from app.services.agent.engine import AgentEngine
from app.services.agent.memory import AgentMemoryService


# ── Exceptions ─────────────────────────────────────────────────────────────────


class AgentNotFound(AppException):
    def __init__(self, agent_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Agent {agent_id} not found")


class AgentRunNotFound(AppException):
    def __init__(self, run_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Agent run {run_id} not found")


class AgentToolNotFound(AppException):
    def __init__(self, tool_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Agent tool {tool_id} not found")


class AgentTemplateNotFound(AppException):
    def __init__(self, template_id: uuid.UUID) -> None:
        super().__init__(
            status_code=404, detail=f"Agent template {template_id} not found"
        )


class AgentTemplateBuiltinError(AppException):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            detail="Built-in templates cannot be modified or deleted",
        )


class AgentDisabledError(AppException):
    def __init__(self, agent_id: uuid.UUID) -> None:
        super().__init__(
            status_code=400,
            detail=f"Agent {agent_id} is disabled and cannot be run",
        )


class AgentRunNotRunningError(AppException):
    def __init__(self, run_id: uuid.UUID) -> None:
        super().__init__(
            status_code=400,
            detail=f"Run {run_id} is not in a running state",
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _apply_list_filters(
    stmt: Select,
    *,
    search: str | None = None,
) -> Select:
    """Apply optional search filter to an agent SELECT."""
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(Agent.name.ilike(like), Agent.description.ilike(like))
        )
    return stmt


async def _fetch_agent_or_raise(
    db: AsyncSession,
    agent_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    load_tools: bool = False,
    load_runs: bool = False,
) -> Agent:
    """Fetch an agent by id, raising 404 if not found or not owned by user."""
    stmt = select(Agent).where(Agent.id == agent_id, Agent.owner_id == user_id)
    if load_tools:
        stmt = stmt.options(joinedload(Agent.tools))
    if load_runs:
        stmt = stmt.options(joinedload(Agent.runs))
    result = await db.execute(stmt)
    agent = result.unique().scalar_one_or_none()
    if agent is None:
        raise AgentNotFound(agent_id)
    return agent


async def _fetch_run_or_raise(
    db: AsyncSession,
    run_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AgentRun:
    """Fetch a run by id, verifying ownership via agent join."""
    result = await db.execute(
        select(AgentRun)
        .join(Agent, AgentRun.agent_id == Agent.id)
        .where(AgentRun.id == run_id, Agent.owner_id == user_id)
    )
    run = result.unique().scalar_one_or_none()
    if run is None:
        raise AgentRunNotFound(run_id)
    return run


def _to_agent_response(agent: Agent) -> AgentResponse:
    """Convert ORM Agent to Pydantic response."""
    return AgentResponse(
        id=agent.id,
        owner_id=agent.owner_id,
        workspace_id=agent.workspace_id,
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        model=agent.model,
        temperature=agent.temperature,
        max_tokens=agent.max_tokens,
        enabled=agent.enabled,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _to_run_response(run: AgentRun) -> AgentRunResponse:
    """Convert ORM AgentRun to Pydantic response."""
    return AgentRunResponse(
        id=run.id,
        agent_id=run.agent_id,
        owner_id=run.owner_id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        input_text=run.input_text,
        result=run.result,
        token_usage=run.token_usage,
        cost=run.cost,
        steps=run.steps,
        logs=run.logs,
        error_message=run.error_message,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def _to_tool_response(tool: AgentTool) -> AgentToolResponse:
    """Convert ORM AgentTool to Pydantic response."""
    return AgentToolResponse(
        id=tool.id,
        agent_id=tool.agent_id,
        tool_type=tool.tool_type,
        name=tool.name,
        description=tool.description,
        config=tool.config,
        enabled=tool.enabled,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


def _to_template_response(tpl: AgentTemplate) -> AgentTemplateResponse:
    """Convert ORM AgentTemplate to Pydantic response."""
    return AgentTemplateResponse(
        id=tpl.id,
        owner_id=tpl.owner_id,
        name=tpl.name,
        description=tpl.description,
        category=tpl.category,
        system_prompt=tpl.system_prompt,
        model=tpl.model,
        temperature=tpl.temperature,
        default_tools=tpl.default_tools,
        is_builtin=tpl.is_builtin,
        is_active=tpl.is_active,
        created_at=tpl.created_at,
        updated_at=tpl.updated_at,
    )


# ── Service ────────────────────────────────────────────────────────────────────


class AgentService:
    """CRUD, execution, and management for AI agents."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._memory_svc = AgentMemoryService(db)

    # ── Agent CRUD ──────────────────────────────────────────────────────────────

    async def create_agent(
        self, data: AgentCreate, user_id: uuid.UUID
    ) -> AgentResponse:
        """Create a new agent for the user."""
        agent = Agent(
            owner_id=user_id,
            name=data.name,
            description=data.description,
            system_prompt=data.system_prompt,
            model=data.model,
            temperature=data.temperature,
            max_tokens=data.max_tokens,
            enabled=data.enabled,
        )
        self.db.add(agent)
        await self.db.commit()
        await self.db.refresh(agent)
        return _to_agent_response(agent)

    async def get_agent(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentResponse:
        """Get a single agent by ID."""
        agent = await _fetch_agent_or_raise(self.db, agent_id, user_id)
        return _to_agent_response(agent)

    async def list_agents(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AgentListResponse:
        """List agents owned by the user with optional search."""
        base = select(Agent).where(Agent.owner_id == user_id)
        base = _apply_list_filters(base, search=search)

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Fetch page
        stmt = (
            base.order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        agents = result.unique().scalars().all()

        return AgentListResponse(
            items=[_to_agent_response(a) for a in agents],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def update_agent(
        self, agent_id: uuid.UUID, data: AgentUpdate, user_id: uuid.UUID
    ) -> AgentResponse:
        """Update an existing agent (partial update)."""
        agent = await _fetch_agent_or_raise(self.db, agent_id, user_id)

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(agent, field, value)

        await self.db.commit()
        await self.db.refresh(agent)
        return _to_agent_response(agent)

    async def delete_agent(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete an agent and its associated runs/memories/tools (CASCADE)."""
        agent = await _fetch_agent_or_raise(self.db, agent_id, user_id)
        await self.db.delete(agent)
        await self.db.commit()

    # ── Run execution ───────────────────────────────────────────────────────────

    async def execute_agent(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        request: AgentRunExecuteRequest,
    ) -> AgentRunExecuteResponse:
        """Execute an agent with the given input and optionally stream.

        This method:
        1. Verifies the agent exists and is enabled
        2. Creates an ``AgentRun`` record (status=queued → running)
        3. Runs the ``AgentEngine``
        4. Updates the run record with results

        If ``request.stream`` is True, the caller should use
        ``execute_agent_stream()`` instead.
        """
        agent = await _fetch_agent_or_raise(
            self.db, agent_id, user_id, load_tools=True
        )
        if not agent.enabled:
            raise AgentDisabledError(agent_id)

        # Create run record
        run = AgentRun(
            agent_id=agent_id,
            owner_id=user_id,
            status="queued",
            input_text=request.input_text,
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        # Update status to running
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        await self.db.commit()

        try:
            # Execute via engine
            engine = AgentEngine(
                db=self.db,
                agent_id=agent_id,
                user_id=user_id,
                run_id=run.id,
            )
            result = await engine.run(input_text=request.input_text)

            # Update run with result
            update_data = result.to_run_update()
            for field, value in update_data.items():
                setattr(run, field, value)

            await self.db.commit()
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            run.finished_at = datetime.now(timezone.utc)
            await self.db.commit()

            return AgentRunExecuteResponse(
                run_id=run.id,
                result=None,
                token_usage={"error": str(exc)},
            )

        return AgentRunExecuteResponse(
            run_id=run.id,
            result=run.result,
            token_usage=run.token_usage,
        )

    # ── Run management ──────────────────────────────────────────────────────────

    async def get_run(
        self, run_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentRunResponse:
        """Get a single run by ID."""
        run = await _fetch_run_or_raise(self.db, run_id, user_id)
        return _to_run_response(run)

    async def list_runs(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AgentRunListResponse:
        """List runs for a specific agent."""
        await _fetch_agent_or_raise(self.db, agent_id, user_id)

        base = select(AgentRun).where(
            AgentRun.agent_id == agent_id,
            AgentRun.owner_id == user_id,
        )
        if status is not None:
            base = base.where(AgentRun.status == status)

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Fetch page
        stmt = (
            base.order_by(AgentRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        runs = result.unique().scalars().all()

        return AgentRunListResponse(
            items=[_to_run_response(r) for r in runs],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def cancel_run(
        self, run_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentRunResponse:
        """Cancel a queued or running run."""
        run = await _fetch_run_or_raise(self.db, run_id, user_id)
        if run.status not in ("queued", "running"):
            raise AgentRunNotRunningError(run_id)

        run.status = "cancelled"
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(run)
        return _to_run_response(run)

    # ── Tool management ─────────────────────────────────────────────────────────

    async def add_tool(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        data: AgentToolCreate,
    ) -> AgentToolResponse:
        """Add a tool to an agent."""
        await _fetch_agent_or_raise(self.db, agent_id, user_id)

        tool = AgentTool(
            agent_id=agent_id,
            tool_type=data.tool_type,
            name=data.name,
            description=data.description,
            config=data.config or {},
            enabled=data.enabled,
        )
        self.db.add(tool)
        await self.db.commit()
        await self.db.refresh(tool)
        return _to_tool_response(tool)

    async def list_tools(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[AgentToolResponse]:
        """List all tools configured for an agent."""
        await _fetch_agent_or_raise(self.db, agent_id, user_id)

        result = await self.db.execute(
            select(AgentTool)
            .where(AgentTool.agent_id == agent_id)
            .order_by(AgentTool.created_at.asc())
        )
        tools = result.unique().scalars().all()
        return [_to_tool_response(t) for t in tools]

    async def update_tool(
        self,
        tool_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        config: dict | None = None,
        enabled: bool | None = None,
    ) -> AgentToolResponse:
        """Update a tool's configuration."""
        result = await self.db.execute(
            select(AgentTool)
            .join(Agent, AgentTool.agent_id == Agent.id)
            .where(AgentTool.id == tool_id, Agent.owner_id == user_id)
        )
        tool = result.unique().scalar_one_or_none()
        if tool is None:
            raise AgentToolNotFound(tool_id)

        if name is not None:
            tool.name = name
        if description is not None:
            tool.description = description
        if config is not None:
            tool.config = config
        if enabled is not None:
            tool.enabled = enabled

        await self.db.commit()
        await self.db.refresh(tool)
        return _to_tool_response(tool)

    async def remove_tool(
        self, tool_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Remove a tool from an agent."""
        result = await self.db.execute(
            select(AgentTool)
            .join(Agent, AgentTool.agent_id == Agent.id)
            .where(AgentTool.id == tool_id, Agent.owner_id == user_id)
        )
        tool = result.unique().scalar_one_or_none()
        if tool is None:
            raise AgentToolNotFound(tool_id)

        await self.db.delete(tool)
        await self.db.commit()

    # ── Template management ─────────────────────────────────────────────────────

    async def create_template(
        self,
        data: AgentTemplateCreate,
        user_id: uuid.UUID,
    ) -> AgentTemplateResponse:
        """Create a new agent template."""
        tpl = AgentTemplate(
            owner_id=user_id,
            name=data.name,
            description=data.description,
            category=data.category,
            system_prompt=data.system_prompt,
            model=data.model,
            temperature=data.temperature,
            default_tools=(
                [dict(t) for t in data.default_tools]
                if data.default_tools
                else None
            ),
            is_builtin=False,
            is_active=True,
        )
        self.db.add(tpl)
        await self.db.commit()
        await self.db.refresh(tpl)
        return _to_template_response(tpl)

    async def list_templates(
        self,
        user_id: uuid.UUID,
        *,
        category: str | None = None,
        include_builtin: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> AgentTemplateListResponse:
        """List available templates.

        Returns built-in templates (``is_builtin=True``) and templates
        created by the user. Optionally filtered by category.
        """
        base = select(AgentTemplate).where(
            AgentTemplate.is_active == True,  # noqa: E712
            or_(
                AgentTemplate.is_builtin == True,  # noqa: E712
                AgentTemplate.owner_id == user_id,
            ),
        )
        if category:
            base = base.where(AgentTemplate.category == category)
        if not include_builtin:
            base = base.where(AgentTemplate.owner_id == user_id)

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Fetch page
        stmt = (
            base.order_by(AgentTemplate.is_builtin.desc(), AgentTemplate.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        templates = result.unique().scalars().all()

        return AgentTemplateListResponse(
            items=[_to_template_response(t) for t in templates],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def get_template(
        self, template_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentTemplateResponse:
        """Get a single template by ID."""
        result = await self.db.execute(
            select(AgentTemplate).where(
                AgentTemplate.id == template_id,
                or_(
                    AgentTemplate.is_builtin == True,  # noqa: E712
                    AgentTemplate.owner_id == user_id,
                ),
            )
        )
        tpl = result.unique().scalar_one_or_none()
        if tpl is None:
            raise AgentTemplateNotFound(template_id)
        return _to_template_response(tpl)

    async def update_template(
        self,
        template_id: uuid.UUID,
        data: AgentTemplateUpdate,
        user_id: uuid.UUID,
    ) -> AgentTemplateResponse:
        """Update a template (fails for built-in templates)."""
        result = await self.db.execute(
            select(AgentTemplate).where(
                AgentTemplate.id == template_id,
            )
        )
        tpl = result.unique().scalar_one_or_none()
        if tpl is None:
            raise AgentTemplateNotFound(template_id)
        if tpl.is_builtin:
            raise AgentTemplateBuiltinError()
        if tpl.owner_id != user_id:
            raise AgentTemplateNotFound(template_id)

        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(tpl, field, value)

        await self.db.commit()
        await self.db.refresh(tpl)
        return _to_template_response(tpl)

    async def delete_template(
        self, template_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        """Delete a template (fails for built-in templates)."""
        result = await self.db.execute(
            select(AgentTemplate).where(
                AgentTemplate.id == template_id,
            )
        )
        tpl = result.unique().scalar_one_or_none()
        if tpl is None:
            raise AgentTemplateNotFound(template_id)
        if tpl.is_builtin:
            raise AgentTemplateBuiltinError()
        if tpl.owner_id != user_id:
            raise AgentTemplateNotFound(template_id)

        await self.db.delete(tpl)
        await self.db.commit()

    async def create_agent_from_template(
        self,
        template_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        name: str | None = None,
    ) -> AgentResponse:
        """Create a new agent by cloning a template's configuration."""
        result = await self.db.execute(
            select(AgentTemplate).where(
                AgentTemplate.id == template_id,
                or_(
                    AgentTemplate.is_builtin == True,  # noqa: E712
                    AgentTemplate.owner_id == user_id,
                ),
            )
        )
        tpl = result.unique().scalar_one_or_none()
        if tpl is None:
            raise AgentTemplateNotFound(template_id)

        agent = Agent(
            owner_id=user_id,
            name=name if name is not None else tpl.name,
            description=tpl.description,
            system_prompt=tpl.system_prompt,
            model=tpl.model,
            temperature=tpl.temperature,
            enabled=True,
        )
        self.db.add(agent)
        await self.db.flush()  # Get agent.id before creating tools

        # Clone default tools from template
        if tpl.default_tools:
            for tool_data in tpl.default_tools:
                tool = AgentTool(
                    agent_id=agent.id,
                    tool_type=tool_data.get("tool_type", ""),
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    config=tool_data.get("config", {}),
                    enabled=True,
                )
                self.db.add(tool)

        await self.db.commit()
        await self.db.refresh(agent)
        return _to_agent_response(agent)
