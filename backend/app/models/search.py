"""Search-related ORM models for the Global Search system.

Covers:
* ``SavedSearch`` — persisted user searches that can be re-run later.
* ``RecentSearch`` — lightweight history of recent searches (auto-pruned).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.user import User


# ── Saved Search ──────────────────────────────────────────────────────────────


class SavedSearch(UUIDMixin, TimestampMixin, Base):
    """A persisted user search that can be re-run later.

    Users can save important or frequent searches (e.g. "all critical bugs
    assigned to me") to quickly re-run them without re-entering the query.
    """

    __tablename__ = "saved_searches"

    # ── Ownership ───────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),  # type: ignore[name-defined]
        nullable=True,
        comment="Future multi-workspace support (reserved)",
    )

    # ── Search data ─────────────────────────────────────────────────
    query: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="The search query text",
    )
    filters: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Optional filters as JSON (status, priority, date ranges, etc.)",
    )

    # ── Relationships ───────────────────────────────────────────────
    owner: Mapped[User] = relationship(
        "User",
        back_populates="saved_searches",
    )

    def __repr__(self) -> str:
        return f"<SavedSearch id={self.id} query={self.query!r}>"


# ── Recent Search ─────────────────────────────────────────────────────────────


class RecentSearch(UUIDMixin, Base):
    """A lightweight search-history entry.

    Recent searches are auto-pruned (e.g. kept to the latest 50 per user)
    to provide quick access to recent queries without manual bookmarking.
    """

    __tablename__ = "recent_searches"

    # ── Ownership ───────────────────────────────────────────────────
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(),  # type: ignore[name-defined]
        nullable=True,
        comment="Future multi-workspace support (reserved)",
    )

    # ── Search data ─────────────────────────────────────────────────
    query: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="The search query text",
    )

    # ── Timestamp ───────────────────────────────────────────────────
    searched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the search was performed",
    )

    # ── Relationships ───────────────────────────────────────────────
    owner: Mapped[User] = relationship(
        "User",
        back_populates="recent_searches",
    )

    def __repr__(self) -> str:
        return f"<RecentSearch id={self.id} query={self.query!r}>"


# ── Late imports (avoid circular dependencies) ──────────────────────────────
from app.models.user import User  # noqa: E402, F811
