"""Pydantic schemas for the AI Agent framework.

Covers CRUD for agents, runs, memories, tools, and templates.
All schemas use ``from_attributes = True`` for ORM compatibility.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Constants ────────────────────────────────────────────────────────────────

AGENT_STATUSES = frozenset({
    "queued", "running", "paused", "completed", "failed", "cancelled", "timed_out",
})
MEMORY_TYPES = frozenset({"short_term", "long_term", "conversation"})
MEMORY_ROLES = frozenset({"user", "assistant", "system"})
TOOL_TYPES = frozenset({
    "knowledge_search", "document_reader", "task_manager", "global_search",
    "chat_history", "calculator", "current_time",
})
TEMPLATE_CATEGORIES = frozenset({
    "general", "research", "coding", "writing", "assistant", "custom",
})


# ── Agent ────────────────────────────────────────────────────────────────────


class AgentCreate(BaseModel):
    """Request to create a new agent."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Agent display name",
    )
    description: str | None = Field(
        None,
        max_length=10000,
        description="Short description of the agent's purpose",
    )
    system_prompt: str | None = Field(
        None,
        max_length=100000,
        description="System prompt that defines the agent's persona and behaviour",
    )
    model: str = Field(
        default="gpt-4o",
        max_length=100,
        description="AI model identifier",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Model temperature",
    )
    max_tokens: int | None = Field(
        None,
        ge=1,
        le=200000,
        description="Maximum tokens per response",
    )
    enabled: bool = Field(
        default=True,
        description="Whether the agent is active and can be run",
    )


class AgentUpdate(BaseModel):
    """Request to update an existing agent (partial update)."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    enabled: bool | None = None


class AgentResponse(BaseModel):
    """Full agent read response."""

    id: UUID
    owner_id: UUID
    workspace_id: UUID | None = None
    name: str
    description: str | None = None
    system_prompt: str | None = None
    model: str
    temperature: float
    max_tokens: int | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    items: list[AgentResponse] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of matching agents")
    offset: int = Field(default=0, description="Offset used for this page")
    limit: int = Field(default=50, description="Limit used for this page")


# ── Agent Run ────────────────────────────────────────────────────────────────


class AgentRunResponse(BaseModel):
    """Full agent run read response."""

    id: UUID
    agent_id: UUID
    owner_id: UUID
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    input_text: str | None = None
    result: str | None = None
    token_usage: dict | None = None
    cost: float | None = None
    steps: dict | None = None
    logs: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentRunListResponse(BaseModel):
    """Paginated list of agent runs."""

    items: list[AgentRunResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    offset: int = Field(default=0)
    limit: int = Field(default=50)


# ── Agent Memory ─────────────────────────────────────────────────────────────


class AgentMemoryResponse(BaseModel):
    """Full agent memory read response."""

    id: UUID
    agent_id: UUID
    run_id: UUID | None = None
    memory_type: str
    role: str | None = None
    content: str
    summary: str | None = None
    memory_metadata: dict | None = None
    importance: float | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentMemoryListResponse(BaseModel):
    """Paginated list of agent memories."""

    items: list[AgentMemoryResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    offset: int = Field(default=0)
    limit: int = Field(default=50)


# ── Agent Tool ───────────────────────────────────────────────────────────────


class AgentToolCreate(BaseModel):
    """Request to add a tool to an agent."""

    tool_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Tool type identifier",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable tool name",
    )
    description: str | None = Field(
        None,
        max_length=10000,
        description="Description of what this tool does",
    )
    config: dict | None = Field(
        None,
        description="Tool-specific configuration",
    )
    enabled: bool = Field(default=True, description="Whether this tool is active")

    @field_validator("tool_type")
    @classmethod
    def validate_tool_type(cls, v: str) -> str:
        if v not in TOOL_TYPES:
            raise ValueError(
                f"Invalid tool_type '{v}'. Must be one of: {', '.join(sorted(TOOL_TYPES))}"
            )
        return v


class AgentToolUpdate(BaseModel):
    """Request to update a tool."""

    name: str | None = None
    description: str | None = None
    config: dict | None = None
    enabled: bool | None = None


class AgentToolResponse(BaseModel):
    """Full agent tool read response."""

    id: UUID
    agent_id: UUID
    tool_type: str
    name: str
    description: str | None = None
    config: dict | None = None
    enabled: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Agent Template ───────────────────────────────────────────────────────────


class AgentTemplateCreate(BaseModel):
    """Request to create a new agent template."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Template display name",
    )
    description: str | None = Field(
        None,
        max_length=10000,
        description="Short description of the template",
    )
    category: str = Field(
        default="general",
        max_length=50,
        description="Template category",
    )
    system_prompt: str | None = Field(
        None,
        max_length=100000,
        description="Default system prompt",
    )
    model: str = Field(
        default="gpt-4o",
        max_length=100,
        description="Default model",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature",
    )
    default_tools: list[dict] | None = Field(
        None,
        description="Default tool set",
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.lower()
        if v not in TEMPLATE_CATEGORIES:
            raise ValueError(
                f"Invalid category '{v}'. Must be one of: {', '.join(sorted(TEMPLATE_CATEGORIES))}"
            )
        return v


class AgentTemplateUpdate(BaseModel):
    """Request to update a template."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    default_tools: list[dict] | None = None
    is_active: bool | None = None


class AgentTemplateResponse(BaseModel):
    """Full agent template read response."""

    id: UUID
    owner_id: UUID | None = None
    name: str
    description: str | None = None
    category: str | None = None
    system_prompt: str | None = None
    model: str
    temperature: float
    default_tools: list[dict] | None = None
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class AgentTemplateListResponse(BaseModel):
    """Paginated list of agent templates."""

    items: list[AgentTemplateResponse] = Field(default_factory=list)
    total: int = Field(default=0)
    offset: int = Field(default=0)
    limit: int = Field(default=50)


# ── Run Execution ────────────────────────────────────────────────────────────


class AgentRunExecuteRequest(BaseModel):
    """Request to execute an agent with input."""

    input_text: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="User-provided input that triggers this run",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response via SSE",
    )


class AgentRunExecuteResponse(BaseModel):
    """Response from executing an agent."""

    run_id: UUID = Field(..., description="ID of the created run")
    result: str | None = Field(None, description="Final output if not streaming")
    token_usage: dict | None = Field(
        None,
        description="Token usage breakdown if available",
    )
