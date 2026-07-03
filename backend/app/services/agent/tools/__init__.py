"""Agent Tool System — pluggable tool definitions.

Each tool is a callable that takes a ``ToolContext`` and returns a
``ToolResult``. Tools are registered by type string and wired into
the runtime via the ``ToolRegistry``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


# ── Types ────────────────────────────────────────────────────────────────────


@dataclass
class ToolContext:
    """Context passed to every tool invocation."""

    user_id: UUID
    agent_id: UUID
    run_id: UUID
    db_session: Any  # AsyncSession
    input_text: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolResult:
    """Result returned by a tool."""

    success: bool
    output: str
    data: dict[str, Any] | None = None
    error: str | None = None


# ── Abstract Tool ────────────────────────────────────────────────────────────


class BaseTool(ABC):
    """Base class for all agent tools."""

    tool_type: str = ""
    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, ctx: ToolContext, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given context and parameters."""
        ...

    def to_tool_def(self) -> dict[str, Any]:
        """Return an OpenAI-compatible tool definition for LLM function calling."""
        return {
            "type": "function",
            "function": {
                "name": self.tool_type,
                "description": self.description,
                "parameters": self.get_parameters_schema(),
            },
        }

    @abstractmethod
    def get_parameters_schema(self) -> dict[str, Any]:
        """Return JSON Schema for this tool's parameters."""
        ...


# ── Registry ─────────────────────────────────────────────────────────────────


class ToolRegistry:
    """Registry of available tools mapped by ``tool_type``."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance by its ``tool_type``."""
        if tool.tool_type in self._tools:
            raise ValueError(f"Tool '{tool.tool_type}' is already registered")
        self._tools[tool.tool_type] = tool

    def get(self, tool_type: str) -> BaseTool | None:
        """Look up a tool by type string."""
        return self._tools.get(tool_type)

    def get_tool_defs(self, tool_types: list[str]) -> list[dict[str, Any]]:
        """Return OpenAI-compatible tool definitions for the given types."""
        defs: list[dict[str, Any]] = []
        for tt in tool_types:
            tool = self._tools.get(tt)
            if tool:
                defs.append(tool.to_tool_def())
        return defs

    def get_all_defs(self) -> list[dict[str, Any]]:
        """Return tool definitions for all registered tools."""
        return [t.to_tool_def() for t in self._tools.values()]
