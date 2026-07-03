"""User ORM model.

Stores authentication credentials, profile information, and
account-verification state.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # ── Authentication ───────────────────────────────────────────
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)

    # ── Profile ──────────────────────────────────────────────────
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Authorization ────────────────────────────────────────────
    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False
    )

    # ── Account State ────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Whether two-factor authentication is enabled (reserved for future use)",
    )

    # ── Login Tracking ────────────────────────────────────────────
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent successful login",
    )

    # ── Email Verification ───────────────────────────────────────
    verification_token_hash: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    verification_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    files: Mapped[list[File]] = relationship(
        "File", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Conversation.updated_at.desc()",
    )
    knowledge_bases: Mapped[list[KnowledgeBase]] = relationship(
        "KnowledgeBase",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    settings: Mapped[UserSettings] = relationship(
        "UserSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    api_provider_configs: Mapped[list[ApiProviderConfig]] = relationship(
        "ApiProviderConfig",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[list[UserSession]] = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    agents: Mapped[list[Agent]] = relationship(
        "Agent",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    agent_templates: Mapped[list[AgentTemplate]] = relationship(
        "AgentTemplate",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    saved_searches: Mapped[list[SavedSearch]] = relationship(
        "SavedSearch",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    recent_searches: Mapped[list[RecentSearch]] = relationship(
        "RecentSearch",
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role!r}>"


# Avoid circular import at runtime
from app.models.conversation import Conversation  # noqa: E402, F811
from app.models.file import File  # noqa: E402, F811
from app.models.knowledge import KnowledgeBase  # noqa: E402, F811
from app.models.refresh_token import RefreshToken  # noqa: E402, F811
from app.models.task import Task  # noqa: E402, F811
from app.models.agent import Agent, AgentTemplate  # noqa: E402, F811
from app.models.search import SavedSearch, RecentSearch  # noqa: E402, F811
from app.models.settings import UserSettings, ApiProviderConfig, UserSession  # noqa: E402, F811
