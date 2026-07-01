"""Pydantic schemas for the Dashboard API.

Provides aggregate statistics, recent activity, usage tracking, and
feed data — all derived from real database tables (conversations,
messages, files).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.storage import FileInfo


class DashboardStats(BaseModel):
    """Aggregate statistics for the current user's dashboard overview."""

    total_conversations: int = Field(
        ...,
        description="Total number of active (non-archived) conversations.",
        json_schema_extra={"example": 12},
    )
    total_messages: int = Field(
        ...,
        description="Total messages across all conversations.",
        json_schema_extra={"example": 342},
    )
    total_files: int = Field(
        ...,
        description="Total number of uploaded files.",
        json_schema_extra={"example": 8},
    )
    total_storage_bytes: int = Field(
        ...,
        description="Aggregate storage used in bytes.",
        json_schema_extra={"example": 5242880},
    )
    total_input_tokens: int = Field(
        ...,
        description="Total AI input tokens consumed.",
        json_schema_extra={"example": 15000},
    )
    total_output_tokens: int = Field(
        ...,
        description="Total AI output tokens consumed.",
        json_schema_extra={"example": 42000},
    )
    total_documents_processed: int = Field(
        default=0,
        description="Number of files that have completed document processing.",
        json_schema_extra={"example": 5},
    )


class RecentChatItem(BaseModel):
    """Conversation summary for the recent-chats widget."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Conversation ID.")
    title: str | None = Field(None, description="Conversation title (may be null).")
    model: str = Field(..., description="AI model used.")
    message_count: int = Field(0, description="Number of messages in this conversation.")
    updated_at: datetime = Field(..., description="Last activity time.")
    created_at: datetime = Field(..., description="Creation time.")


class RecentActivityItem(BaseModel):
    """A single entry in the activity feed."""

    id: UUID = Field(..., description="ID of the source entity.")
    type: str = Field(
        ...,
        description="Activity category: 'chat', 'upload', or 'message'.",
        json_schema_extra={"example": "chat"},
    )
    description: str = Field(
        ...,
        description="Human-readable activity summary.",
        json_schema_extra={"example": "Started conversation \"Project Ideas\""},
    )
    created_at: datetime = Field(
        ...,
        description="When the activity occurred.",
    )


class DailyTokenUsage(BaseModel):
    """Token consumption for a single calendar day."""

    date: str = Field(
        ...,
        description="Date in YYYY-MM-DD format.",
        json_schema_extra={"example": "2026-07-01"},
    )
    input_tokens: int = Field(0, description="Input tokens used on this day.")
    output_tokens: int = Field(0, description="Output tokens used on this day.")


class UsageResponse(BaseModel):
    """Detailed usage analytics with daily breakdown."""

    total_input_tokens: int = Field(..., description="Lifetime input tokens.")
    total_output_tokens: int = Field(..., description="Lifetime output tokens.")
    total_messages: int = Field(..., description="Total assistant messages.")
    total_conversations: int = Field(..., description="Total active conversations.")
    daily_usage: list[DailyTokenUsage] = Field(
        default_factory=list,
        description="Daily token breakdown for the last 30 days.",
    )
    storage_total_bytes: int = Field(..., description="Total storage used.")
    storage_total_files: int = Field(..., description="Total files stored.")


class DashboardResponse(BaseModel):
    """Top-level aggregate feed returned by GET /api/v1/dashboard."""

    stats: DashboardStats = Field(..., description="Aggregate statistics.")
    recent_chats: list[RecentChatItem] = Field(
        default_factory=list,
        description="Most recently updated conversations.",
    )
    recent_files: list[FileInfo] = Field(
        default_factory=list,
        description="Most recently uploaded files.",
    )
    recent_activity: list[RecentActivityItem] = Field(
        default_factory=list,
        description="Recent activity feed entries.",
    )
