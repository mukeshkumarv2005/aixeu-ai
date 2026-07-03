"""Agent management API router.

Provides full CRUD endpoints for AI agents, their runs, tools,
and templates.  All endpoints are ownership-gated via the
``get_current_active_user`` dependency.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, get_current_active_user
from app.models.user import User
from app.schemas.agent import (
    AGENT_STATUSES,
    TOOL_TYPES,
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
from app.services.agent import (
    AgentDisabledError,
    AgentNotFound,
    AgentRunNotFound,
    AgentRunNotRunningError,
    AgentService,
    AgentTemplateBuiltinError,
    AgentTemplateNotFound,
    AgentToolNotFound,
)

router = APIRouter()


# ── Agent CRUD (static routes) ───────────────────────────────────────────────────


@router.post(
    "/agents",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent",
    description=(
        "Create a new AI agent owned by the current user.  Accepts all "
        "fields from the ``AgentCreate`` schema including system prompt, "
        "model, temperature, and max tokens."
    ),
)
async def create_agent(
    body: AgentCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentResponse:
    """Create a new AI agent."""
    service = AgentService(db)
    return await service.create_agent(body, current_user.id)


@router.get(
    "/agents",
    response_model=AgentListResponse,
    summary="List agents",
    description=(
        "Return a paginated list of agents owned by the current user. "
        "Supports optional search filtering by name or description."
    ),
)
async def list_agents(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    search: str | None = Query(
        None, min_length=1, description="Search in name and description"
    ),
    offset: int = Query(
        0, ge=0, le=1000, description="Number of records to skip (max 1000)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> AgentListResponse:
    """List agents with optional search and pagination."""
    service = AgentService(db)
    return await service.list_agents(
        current_user.id, search=search, offset=offset, limit=limit
    )


# ── Template Management (must come before /agents/{agent_id} for routing) ──────


@router.post(
    "/agents/templates",
    response_model=AgentTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create template",
    description=(
        "Create a new agent template owned by the current user.  "
        "Built-in templates cannot be created — the built-in "
        "flag is set automatically to ``False``."
    ),
)
async def create_template(
    body: AgentTemplateCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentTemplateResponse:
    """Create a new agent template."""
    service = AgentService(db)
    return await service.create_template(body, current_user.id)


@router.get(
    "/agents/templates",
    response_model=AgentTemplateListResponse,
    summary="List templates",
    description=(
        "Return available templates.  Includes both built-in templates "
        "and templates created by the current user.  Optionally filtered "
        "by category."
    ),
)
async def list_templates(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    category: str | None = Query(
        None, description="Filter by template category"
    ),
    include_builtin: bool = Query(
        True, description="Whether to include built-in templates"
    ),
    offset: int = Query(
        0, ge=0, le=1000, description="Number of records to skip (max 1000)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> AgentTemplateListResponse:
    """List available agent templates."""
    service = AgentService(db)
    return await service.list_templates(
        current_user.id,
        category=category,
        include_builtin=include_builtin,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/agents/templates/{template_id}",
    response_model=AgentTemplateResponse,
    summary="Get template",
    description=(
        "Return a single template by ID.  Both built-in templates and "
        "user-created templates are accessible."
    ),
)
async def get_template(
    template_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentTemplateResponse:
    """Get a single template by ID."""
    service = AgentService(db)
    try:
        return await service.get_template(template_id, current_user.id)
    except AgentTemplateNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


@router.patch(
    "/agents/templates/{template_id}",
    response_model=AgentTemplateResponse,
    summary="Update template",
    description=(
        "Partial update of a user-created template.  Built-in templates "
        "cannot be modified — returns 403."
    ),
)
async def update_template(
    template_id: uuid.UUID,
    body: AgentTemplateUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentTemplateResponse:
    """Update a template (fails for built-in templates)."""
    service = AgentService(db)
    try:
        return await service.update_template(template_id, body, current_user.id)
    except AgentTemplateNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    except AgentTemplateBuiltinError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in templates cannot be modified",
        )


@router.delete(
    "/agents/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete template",
    description=(
        "Delete a user-created template.  Built-in templates cannot "
        "be deleted — returns 403."
    ),
)
async def delete_template(
    template_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a template (fails for built-in templates)."""
    service = AgentService(db)
    try:
        await service.delete_template(template_id, current_user.id)
    except AgentTemplateNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    except AgentTemplateBuiltinError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in templates cannot be deleted",
        )


@router.post(
    "/agents/templates/{template_id}/create-agent",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create agent from template",
    description=(
        "Create a new agent by cloning a template's configuration. "
        "The agent is created with the template's system prompt, model, "
        "temperature, and default tools."
    ),
)
async def create_agent_from_template(
    template_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    name: str | None = Query(None, description="Optional name override for the new agent"),
) -> AgentResponse:
    """Create an agent from a template."""
    service = AgentService(db)
    try:
        return await service.create_agent_from_template(
            template_id, current_user.id, name=name
        )
    except AgentTemplateNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )


# ── Agent CRUD (parameterized routes) ──────────────────────────────────────────


@router.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent",
    description=(
        "Return a single agent by ID.  Ownership-gated — returns 404 "
        "for another user's agent."
    ),
)
async def get_agent(
    agent_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentResponse:
    """Get a single agent by ID."""
    service = AgentService(db)
    try:
        return await service.get_agent(agent_id, current_user.id)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.patch(
    "/agents/{agent_id}",
    response_model=AgentResponse,
    summary="Update agent",
    description=(
        "Partial update of an agent.  Only the fields provided in the "
        "request body are changed.  Ownership-gated — returns 404 for "
        "another user's agent."
    ),
)
async def update_agent(
    agent_id: uuid.UUID,
    body: AgentUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentResponse:
    """Update an agent (partial update)."""
    service = AgentService(db)
    try:
        return await service.update_agent(agent_id, body, current_user.id)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete agent",
    description=(
        "Delete an agent and all associated runs, memories, and tools "
        "(cascade).  Ownership-gated — returns 404 for another user's agent."
    ),
)
async def delete_agent(
    agent_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete an agent."""
    service = AgentService(db)
    try:
        await service.delete_agent(agent_id, current_user.id)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


# ── Agent Execution ─────────────────────────────────────────────────────────────


@router.post(
    "/agents/{agent_id}/execute",
    response_model=AgentRunExecuteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute agent",
    description=(
        "Execute an agent with the given input text.  The agent runs "
        "its plan-execute-reflect reasoning loop and returns the final "
        "output along with token usage.  The agent must be enabled."
    ),
)
async def execute_agent(
    agent_id: uuid.UUID,
    body: AgentRunExecuteRequest,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentRunExecuteResponse:
    """Execute an agent with input text."""
    service = AgentService(db)
    try:
        return await service.execute_agent(agent_id, current_user.id, body)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    except AgentDisabledError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is disabled and cannot be executed",
        )


# ── Run Management ──────────────────────────────────────────────────────────────


@router.get(
    "/agents/{agent_id}/runs",
    response_model=AgentRunListResponse,
    summary="List runs",
    description=(
        "Return a paginated list of runs for a specific agent, "
        "optionally filtered by status."
    ),
)
async def list_runs(
    agent_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    run_status: str | None = Query(
        None,
        alias="status",
        description="Filter by run status",
    ),
    offset: int = Query(
        0, ge=0, le=1000, description="Number of records to skip (max 1000)"
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum records to return"
    ),
) -> AgentRunListResponse:
    """List runs for an agent."""
    service = AgentService(db)
    try:
        return await service.list_runs(
            agent_id,
            current_user.id,
            status=run_status,
            offset=offset,
            limit=limit,
        )
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.get(
    "/agents/runs/{run_id}",
    response_model=AgentRunResponse,
    summary="Get run",
    description=(
        "Return a single agent run by ID.  Ownership-gated via "
        "agent-owner join — returns 404 for another user's run."
    ),
)
async def get_run(
    run_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentRunResponse:
    """Get a single run by ID."""
    service = AgentService(db)
    try:
        return await service.get_run(run_id, current_user.id)
    except AgentRunNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )


@router.post(
    "/agents/runs/{run_id}/cancel",
    response_model=AgentRunResponse,
    summary="Cancel run",
    description=(
        "Cancel a queued or running agent run.  Idempotent — cancelling "
        "an already-finished run returns a 400 error."
    ),
)
async def cancel_run(
    run_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentRunResponse:
    """Cancel a queued or running run."""
    service = AgentService(db)
    try:
        return await service.cancel_run(run_id, current_user.id)
    except AgentRunNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )
    except AgentRunNotRunningError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Run is not in a running or queued state",
        )


# ── Tool Management ─────────────────────────────────────────────────────────────


@router.post(
    "/agents/{agent_id}/tools",
    response_model=AgentToolResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tool",
    description=(
        "Add a tool to an agent.  The tool type must be one of the "
        "registered tool types.  Returns the created tool configuration."
    ),
)
async def add_tool(
    agent_id: uuid.UUID,
    body: AgentToolCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentToolResponse:
    """Add a tool to an agent."""
    service = AgentService(db)
    try:
        return await service.add_tool(agent_id, current_user.id, body)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.get(
    "/agents/{agent_id}/tools",
    response_model=list[AgentToolResponse],
    summary="List tools",
    description="List all tools configured for an agent.",
)
async def list_tools(
    agent_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> list[AgentToolResponse]:
    """List tools for an agent."""
    service = AgentService(db)
    try:
        return await service.list_tools(agent_id, current_user.id)
    except AgentNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )


@router.patch(
    "/agents/tools/{tool_id}",
    response_model=AgentToolResponse,
    summary="Update tool",
    description=(
        "Partial update of a tool's configuration.  Ownership-gated "
        "via agent-owner join — returns 404 for another user's tool."
    ),
)
async def update_tool(
    tool_id: uuid.UUID,
    body: dict,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> AgentToolResponse:
    """Update a tool's configuration."""
    service = AgentService(db)
    try:
        return await service.update_tool(
            tool_id,
            current_user.id,
            name=body.get("name"),
            description=body.get("description"),
            config=body.get("config"),
            enabled=body.get("enabled"),
        )
    except AgentToolNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )


@router.delete(
    "/agents/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tool",
    description=(
        "Remove a tool from an agent.  Ownership-gated via "
        "agent-owner join — returns 404 for another user's tool."
    ),
)
async def remove_tool(
    tool_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove a tool from an agent."""
    service = AgentService(db)
    try:
        await service.remove_tool(tool_id, current_user.id)
    except AgentToolNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )


