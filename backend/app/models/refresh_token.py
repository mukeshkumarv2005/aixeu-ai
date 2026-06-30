"""RefreshToken ORM model.

Tracks issued refresh tokens and their revocation state for rotation
and theft-detection semantics (see ``app/api/v1/auth.py``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class RefreshToken(UUIDMixin, Base):
    __tablename__ = "refresh_tokens"

    # ── Foreign Key ──────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # ── Token Identity (JWT ID) ──────────────────────────────────
    jti: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )

    # ── Lifecycle ────────────────────────────────────────────────
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="refresh_tokens"
    )

    @property
    def is_revoked(self) -> bool:
        """Return True if this token has been revoked."""
        return self.revoked_at is not None

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} jti={self.jti!r} "
            f"revoked={self.is_revoked}>"
        )


# Avoid circular import
from app.models.user import User  # noqa: E402, F811
