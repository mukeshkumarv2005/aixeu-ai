"""Agent execution engine — multi-step reasoning loop with tool calling.

The ``AgentEngine`` implements a plan-execute-reflect loop:

1. Load agent configuration, conversation history, and tool definitions
2. Build an OpenAI-compatible message array (system prompt + history + input)
3. Call ``AIProvider.chat_completion()`` with the tool definitions
4. If the model requests tool calls → execute each via ``ToolRegistry``
5. Feed tool results back to the model (reflect step)
6. Repeat until the model returns plain text or the iteration limit is reached
7. Save conversation turns and short-term memories
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.agent import Agent, AgentRun, AgentTool
from app.services.ai import AIProvider, ChatCompletionResult, ToolCall, get_ai_provider
from app.services.agent.memory import AgentMemoryService
from app.services.agent.tools import BaseTool, ToolContext, ToolRegistry, ToolResult


# ── Constants ──────────────────────────────────────────────────────────────────

MAX_REASONING_ITERATIONS = 10
"""Hard limit on tool-calling cycles to prevent infinite loops."""

TOOL_CALL_RESULT_ROLE = "tool"
"""Role string used for tool-result messages sent back to the model."""


# ── Engine ─────────────────────────────────────────────────────────────────────


class AgentEngine:
    """Multi-step reasoning engine for AI agents.

    Usage::

        engine = AgentEngine(db, agent_id, user_id)
        result = await engine.run(input_text="What's the weather?")
    """

    def __init__(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
        *,
        ai_provider: AIProvider | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        self.db = db
        self.agent_id = agent_id
        self.user_id = user_id
        self.run_id = run_id or uuid.uuid4()

        self._ai = ai_provider or get_ai_provider()
        self._tools = tool_registry or ToolRegistry()
        self._memory_svc = AgentMemoryService(db)

        # Accumulated token counts across all turns
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

    # ── Public API ──────────────────────────────────────────────────────────

    async def run(
        self,
        input_text: str,
        *,
        max_iterations: int = MAX_REASONING_ITERATIONS,
    ) -> AgentRunResult:
        """Execute the agent reasoning loop.

        Args:
            input_text: The user's input message.
            max_iterations: Maximum number of tool-calling cycles.

        Returns:
            An ``AgentRunResult`` with the final output, token usage, and
            execution metadata.
        """
        agent = await self._load_agent()
        conversation = await self._memory_svc.get_conversation_history(
            self.agent_id, self.user_id
        )
        tool_defs = await self._load_tool_defs(agent)
        messages = self._build_messages(agent, conversation, input_text)

        steps: list[dict[str, Any]] = []
        iteration_count = 0
        final_content: str | None = None
        start_time = datetime.now(timezone.utc)

        while iteration_count < max_iterations:
            iteration_count += 1

            # ── Call the model ─────────────────────────────────────────────
            result = await self._ai.chat_completion(
                messages=messages,
                tools=tool_defs,
                model=agent.model,
                temperature=agent.temperature,
                max_tokens=agent.max_tokens,
            )

            if result.input_tokens:
                self.total_input_tokens += result.input_tokens
            if result.output_tokens:
                self.total_output_tokens += result.output_tokens

            # ── Handle tool calls ──────────────────────────────────────────
            if result.tool_calls:
                # Add the assistant's tool-call message to the conversation
                messages.append(self._build_assistant_tool_msg(result))

                # Execute each tool and collect results
                for tc in result.tool_calls:
                    step = {
                        "iteration": iteration_count,
                        "tool_call_id": tc.id,
                        "tool_name": tc.function.get("name", ""),
                        "arguments": tc.function.get("arguments", "{}"),
                        "started_at": datetime.now(timezone.utc).isoformat(),
                    }

                    try:
                        tool_result = await self._execute_tool(
                            agent, tc, input_text
                        )
                        step["success"] = tool_result.success
                        step["output"] = tool_result.output[:2000]
                        step["finished_at"] = datetime.now(timezone.utc).isoformat()

                        # Feed the tool result back as a new message
                        messages.append(
                            {
                                "role": TOOL_CALL_RESULT_ROLE,
                                "tool_call_id": tc.id,
                                "content": tool_result.output[:5000],
                            }
                        )
                    except Exception as exc:
                        step["success"] = False
                        step["error"] = str(exc)
                        step["finished_at"] = datetime.now(timezone.utc).isoformat()
                        messages.append(
                            {
                                "role": TOOL_CALL_RESULT_ROLE,
                                "tool_call_id": tc.id,
                                "content": f"Tool execution error: {exc}",
                            }
                        )

                    steps.append(step)

                # Loop back for reflection
                continue

            # ── No tool calls → final response ─────────────────────────────
            final_content = result.content or ""
            break

        end_time = datetime.now(timezone.utc)

        # ── Save conversation turns to memory ─────────────────────────────
        await self._save_conversation(input_text, final_content)
        await self._memory_svc.prune_short_term(self.agent_id, self.user_id)

        return AgentRunResult(
            output=final_content,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            iterations=iteration_count,
            steps=steps,
            started_at=start_time,
            finished_at=end_time,
        )

    # ── Internal: data loading ─────────────────────────────────────────────

    async def _load_agent(self) -> Agent:
        """Fetch the agent with its tool relationships loaded."""
        result = await self.db.execute(
            select(Agent)
            .options(joinedload(Agent.tools))
            .where(Agent.id == self.agent_id, Agent.owner_id == self.user_id)
        )
        agent = result.unique().scalar_one_or_none()
        if agent is None:
            from app.services.agent.memory import AgentNotFound

            raise AgentNotFound(self.agent_id)
        return agent

    async def _load_tool_defs(self, agent: Agent) -> list[dict[str, Any]]:
        """Build OpenAI-compatible tool definitions from the agent's enabled tools.

        Only includes tools that are both registered in the ``ToolRegistry``
        and enabled in the agent's configuration.
        """
        enabled_tools = [t for t in (agent.tools or []) if t.enabled]
        tool_types = [t.tool_type for t in enabled_tools]
        return self._tools.get_tool_defs(tool_types)

    # ── Internal: message building ─────────────────────────────────────────

    def _build_messages(
        self,
        agent: Agent,
        conversation: Sequence[Any],
        input_text: str,
    ) -> list[dict[str, Any]]:
        """Construct the OpenAI-format message list.

        Order: system prompt → conversation history → current user input.
        """
        messages: list[dict[str, Any]] = []

        # System prompt
        if agent.system_prompt:
            messages.append({"role": "system", "content": agent.system_prompt})

        # Conversation history (from memory service)
        for mem in conversation:
            messages.append(
                {
                    "role": mem.role or "assistant",
                    "content": mem.content,
                }
            )

        # Current user input
        messages.append({"role": "user", "content": input_text})

        return messages

    @staticmethod
    def _build_assistant_tool_msg(
        result: ChatCompletionResult,
    ) -> dict[str, Any]:
        """Build an assistant message containing tool calls.

        The OpenAI API expects tool_calls nested inside the assistant message.
        """
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": result.content or "",
        }
        if result.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": tc.function,
                }
                for tc in result.tool_calls
            ]
        return msg

    # ── Internal: tool execution ───────────────────────────────────────────

    async def _execute_tool(
        self,
        agent: Agent,
        tc: ToolCall,
        input_text: str,
    ) -> ToolResult:
        """Look up the tool in the registry and execute it with parsed args."""
        tool_name = tc.function.get("name", "")
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                output=f"Unknown tool: {tool_name}",
                error=f"No tool registered with type '{tool_name}'",
            )

        # Parse arguments
        args_raw = tc.function.get("arguments", "{}")
        try:
            args = json.loads(args_raw)
        except json.JSONDecodeError as exc:
            return ToolResult(
                success=False,
                output=f"Invalid tool arguments JSON: {exc}",
                error=str(exc),
            )

        # Build context
        ctx = ToolContext(
            user_id=self.user_id,
            agent_id=self.agent_id,
            run_id=self.run_id,
            db_session=self.db,
            input_text=input_text,
        )

        return await tool.execute(ctx, **args)

    # ── Internal: memory persistence ───────────────────────────────────────

    async def _save_conversation(
        self,
        input_text: str,
        final_content: str | None,
    ) -> None:
        """Save the user input and agent response as conversation memories."""
        # User turn
        await self._memory_svc.add_conversation_turn(
            agent_id=self.agent_id,
            user_id=self.user_id,
            role="user",
            content=input_text[:50000],
            run_id=self.run_id,
            importance=0.5,
        )

        # Assistant turn (if there was a final response)
        if final_content:
            await self._memory_svc.add_conversation_turn(
                agent_id=self.agent_id,
                user_id=self.user_id,
                role="assistant",
                content=final_content[:50000],
                run_id=self.run_id,
                importance=0.5,
            )


# ── Result type ────────────────────────────────────────────────────────────────


@dataclass
class AgentRunResult:
    """Result of a single agent execution."""

    output: str | None
    input_tokens: int
    output_tokens: int
    iterations: int
    steps: list[dict[str, Any]]
    started_at: datetime
    finished_at: datetime

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def duration_seconds(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()

    def to_run_update(self) -> dict[str, Any]:
        """Return a dict suitable for updating an ``AgentRun`` ORM row."""
        return {
            "status": "completed",
            "result": self.output,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "token_usage": {
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "total_tokens": self.total_tokens,
            },
            "steps": self.steps,
        }


