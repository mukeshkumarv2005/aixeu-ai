"""File ORM model.

Represents an uploaded file owned by a user.  The file contents are
managed by a ``StorageProvider`` implementation, while this model
tracks the metadata (name, type, size, internal path).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class File(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "files"

    # ── Ownership ──────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Metadata ───────────────────────────────────────────────────
    filename: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="Original filename"
    )
    mime_type: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="MIME type (e.g. image/png)"
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="File size in bytes"
    )
    storage_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Path returned by the storage provider",
    )

    # ── Flags ─────────────────────────────────────────────────────
    is_temporary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether the file can be garbage-collected",
    )

    # ── Relationships ──────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="files"
    )

    def __repr__(self) -> str:
        return (
            f"<File id={self.id} filename={self.filename!r} "
            f"size={self.size_bytes} user_id={self.user_id}>"
        )


# Avoid circular import at runtime
from app.models.user import User  # noqa: E402, F811
