"""Declarative base, common mixins, and utility columns.

Every model in the application inherits from ``Base``.  The mixins
defined here provide a standard UUID primary key and auto-managed
``created_at`` / ``updated_at`` timestamps.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all Aevix ORM models."""

    pass


class UUIDMixin:
    """Mixin that adds a UUID primary key column named ``id``."""

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Mixin that adds ``created_at`` and ``updated_at`` timestamp columns.

    Both columns are timezone-aware and default to ``UTC``.
    ``updated_at`` is refreshed on every row update.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=datetime.now(UTC),
        nullable=True,
    )
