"""Pydantic schemas for the AI Chat feature.

Covers conversation CRUD, message history, and streaming chunks.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ─── Conversation ────────────────────────────────────────────────────────────


class ConversationCreate(BaseModel):
    title: str | None = None
    model: str = "gpt-4o"


class ConversationUpdate(BaseModel):
    title: str | None = None
    is_archived: bool | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str | None
    model: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime | None
    message_count: int = 0


class ConversationList(BaseModel):
    conversations: list[ConversationResponse]
    total: int


# ─── Message ─────────────────────────────────────────────────────────────────


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    model: str | None = None
    created_at: datetime


class MessageList(BaseModel):
    messages: list[MessageResponse]
    total: int


class MessageSend(BaseModel):
    """Request body to send a message to the AI."""

    content: str
    model: str | None = None  # override the conversation's default model


# ─── Streaming ───────────────────────────────────────────────────────────────


class StreamChunk(BaseModel):
    """A single streaming chunk sent via SSE."""

    type: str  # "chunk" | "done" | "error" | "title"
    content: str = ""
    finish_reason: str | None = None
    message_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
