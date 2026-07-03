"""Agent memory management service — CRUD, pruning, and conversation history.

The ``AgentMemoryService`` follows the same service-layer pattern as
``TaskService``: a class that takes ``AsyncSession``, raises
``AppException`` subclasses for 4xx errors, and enforces agent-ownership
isolation on all queries.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.agent import Agent, AgentMemory
from app.models.user import User


# ── Exceptions ─────────────────────────────────────────────────────────────────


class AgentNotFound(AppException):
    """Raised when an agent does not exist or is not owned by the user."""

    def __init__(self, agent_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Agent {agent_id} not found")


class MemoryNotFound(AppException):
    """Raised when a memory entry does not exist."""

    def __init__(self, memory_id: uuid.UUID) -> None:
        super().__init__(status_code=404, detail=f"Memory {memory_id} not found")


# ── Constants ──────────────────────────────────────────────────────────────────

MEMORY_TYPES = {"short_term", "long_term", "conversation"}
MEMORY_ROLES = {"user", "assistant", "system"}

# Maximum number of short-term memories to retain before pruning
SHORT_TERM_MAX = 50

# Default TTL for short-term memories (1 hour)
SHORT_TERM_TTL_SECONDS = 3600


# ── Service ────────────────────────────────────────────────────────────────────


class AgentMemoryService:
    """CRUD and management for agent memories, scoped to a user session."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _fetch_agent_or_raise(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> Agent:
        """Verify the agent exists and is owned by *user_id*."""
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id, Agent.owner_id == user_id)
        )
        agent = result.unique().scalar_one_or_none()
        if agent is None:
            raise AgentNotFound(agent_id)
        return agent

    async def _fetch_memory_or_raise(
        self, memory_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentMemory:
        """Fetch a memory entry, verifying agent ownership via join."""
        result = await self.db.execute(
            select(AgentMemory)
            .join(Agent, AgentMemory.agent_id == Agent.id)
            .where(AgentMemory.id == memory_id, Agent.owner_id == user_id)
        )
        memory = result.unique().scalar_one_or_none()
        if memory is None:
            raise MemoryNotFound(memory_id)
        return memory

    # ── Create ───────────────────────────────────────────────────────────────

    async def add_memory(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        memory_type: str = "short_term",
        role: str | None = None,
        content: str,
        summary: str | None = None,
        metadata: dict | None = None,
        importance: float = 0.0,
        run_id: uuid.UUID | None = None,
        expires_at: datetime | None = None,
    ) -> AgentMemory:
        """Add a memory entry for an agent.

        Args:
            agent_id: The agent to attach the memory to.
            user_id: The owning user (used for access control).
            memory_type: ``short_term``, ``long_term``, or ``conversation``.
            role: Message role (user/assistant/system) for conversation memories.
            content: Memory content text.
            summary: Optional compressed summary.
            metadata: Arbitrary metadata dict.
            importance: Importance score 0.0–1.0.
            run_id: Optional link to the run that created this memory.
            expires_at: Optional TTL; memory is pruned after this time.

        Returns:
            The newly created ``AgentMemory`` row.
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        mem = AgentMemory(
            agent_id=agent_id,
            run_id=run_id,
            memory_type=memory_type,
            role=role,
            content=content,
            summary=summary,
            memory_metadata=metadata or {},
            importance=importance,
            expires_at=expires_at or self._default_expiry(memory_type),
        )
        self.db.add(mem)
        await self.db.commit()
        await self.db.refresh(mem)
        return mem

    async def add_conversation_turn(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        role: str,
        content: str,
        run_id: uuid.UUID | None = None,
        importance: float = 0.1,
    ) -> AgentMemory:
        """Convenience: add a single conversation turn as a memory entry."""
        return await self.add_memory(
            agent_id=agent_id,
            user_id=user_id,
            memory_type="conversation",
            role=role,
            content=content,
            run_id=run_id,
            importance=importance,
        )

    # ── Read ─────────────────────────────────────────────────────────────────

    async def get_memory(
        self, memory_id: uuid.UUID, user_id: uuid.UUID
    ) -> AgentMemory:
        """Get a single memory entry by ID."""
        return await self._fetch_memory_or_raise(memory_id, user_id)

    async def list_memories(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        memory_type: str | None = None,
        role: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[AgentMemory], int]:
        """List memories for an agent with optional type/role filters.

        Returns:
            A tuple of ``(rows, total_count)``.
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        base = select(AgentMemory).where(AgentMemory.agent_id == agent_id)

        if memory_type is not None:
            base = base.where(AgentMemory.memory_type == memory_type)
        if role is not None:
            base = base.where(AgentMemory.role == role)

        # Count
        count_q = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_q)).scalar_one()

        # Fetch page
        stmt = (
            base.order_by(AgentMemory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.unique().scalars().all()

        return rows, total

    async def get_conversation_history(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        limit: int = 50,
        run_id: uuid.UUID | None = None,
    ) -> Sequence[AgentMemory]:
        """Retrieve recent conversation turns for context window building.

        Args:
            agent_id: Agent to fetch conversation for.
            user_id: Owning user.
            limit: Max conversation turns to retrieve.
            run_id: If set, only returns memories from this specific run.

        Returns:
            Conversation memories ordered by creation time (oldest first).
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == agent_id,
                AgentMemory.memory_type == "conversation",
            )
            .order_by(AgentMemory.created_at.asc())
        )
        if run_id is not None:
            stmt = stmt.where(AgentMemory.run_id == run_id)

        result = await self.db.execute(stmt.limit(limit))
        return result.unique().scalars().all()

    async def search_memories(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        *,
        memory_type: str | None = None,
        limit: int = 20,
    ) -> Sequence[AgentMemory]:
        """Search memory content by keyword (case-insensitive ILIKE).

        Args:
            agent_id: Agent to search within.
            user_id: Owning user.
            query: Search term.
            memory_type: Optional filter (short_term/long_term/conversation).
            limit: Max results.

        Returns:
            Matching memory rows ordered by importance descending.
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        like = f"%{query}%"
        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.agent_id == agent_id,
                or_(
                    AgentMemory.content.ilike(like),
                    AgentMemory.summary.ilike(like),
                ),
            )
            .order_by(AgentMemory.importance.desc(), AgentMemory.created_at.desc())
        )
        if memory_type is not None:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)

        result = await self.db.execute(stmt.limit(limit))
        return result.unique().scalars().all()

    # ── Update ───────────────────────────────────────────────────────────────

    async def update_memory(
        self,
        memory_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        content: str | None = None,
        summary: str | None = None,
        importance: float | None = None,
        metadata: dict | None = None,
    ) -> AgentMemory:
        """Update a memory entry's content, summary, importance, or metadata."""
        mem = await self._fetch_memory_or_raise(memory_id, user_id)

        if content is not None:
            mem.content = content
        if summary is not None:
            mem.summary = summary
        if importance is not None:
            mem.importance = importance
        if metadata is not None:
            mem.memory_metadata = metadata

        await self.db.commit()
        await self.db.refresh(mem)
        return mem

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_memory(self, memory_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a single memory entry."""
        mem = await self._fetch_memory_or_raise(memory_id, user_id)
        await self.db.delete(mem)
        await self.db.commit()

    async def clear_agent_memories(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        memory_type: str | None = None,
    ) -> int:
        """Delete all memories for an agent, optionally filtered by type.

        Returns:
            Number of deleted rows.
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        stmt = delete(AgentMemory).where(AgentMemory.agent_id == agent_id)
        if memory_type is not None:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    # ── Pruning ─────────────────────────────────────────────────────────────

    async def prune_expired(self) -> int:
        """Remove all memory entries past their ``expires_at`` time.

        This is a system-level operation — it does not filter by user/agent.

        Returns:
            Number of deleted rows.
        """
        now = datetime.now(timezone.utc)
        stmt = delete(AgentMemory).where(AgentMemory.expires_at < now)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def prune_short_term(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        """Trim short-term memories to the most recent ``SHORT_TERM_MAX`` entries.

        Keeps the highest-importance entries within the cap, deleting the rest.

        Returns:
            Number of deleted rows.
        """
        await self._fetch_agent_or_raise(agent_id, user_id)

        # Get IDs of short-term memories ordered by importance then recency
        result = await self.db.execute(
            select(AgentMemory.id)
            .where(
                AgentMemory.agent_id == agent_id,
                AgentMemory.memory_type == "short_term",
            )
            .order_by(
                AgentMemory.importance.desc(),
                AgentMemory.created_at.desc(),
            )
        )
        all_ids: list[uuid.UUID] = list(result.scalars().all())

        if len(all_ids) <= SHORT_TERM_MAX:
            return 0

        # IDs beyond the cap get deleted
        ids_to_delete = all_ids[SHORT_TERM_MAX:]
        stmt = delete(AgentMemory).where(AgentMemory.id.in_(ids_to_delete))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    # ── Summary / stats ──────────────────────────────────────────────────────

    async def memory_stats(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> dict[str, int]:
        """Return per-type memory counts for an agent."""
        await self._fetch_agent_or_raise(agent_id, user_id)

        counts: dict[str, int] = {}
        for mt in ("short_term", "long_term", "conversation"):
            result = await self.db.execute(
                select(func.count(AgentMemory.id)).where(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.memory_type == mt,
                )
            )
            counts[mt] = result.scalar_one()
        counts["total"] = sum(counts.values())
        return counts

    # ── Private helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _default_expiry(memory_type: str) -> datetime | None:
        """Return a default ``expires_at`` based on memory type."""
        now = datetime.now(timezone.utc)
        if memory_type == "short_term":
            return now + timedelta(seconds=SHORT_TERM_TTL_SECONDS)
        if memory_type == "conversation":
            return now + timedelta(days=7)
        # long_term — no expiry
        return None
