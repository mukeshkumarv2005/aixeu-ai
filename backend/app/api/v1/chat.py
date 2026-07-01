"""AI Chat API router.

Provides conversation management and streaming chat completions.
All endpoints are ownership-gated to the current user.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.api.deps import DbSession, get_current_active_user
from app.models.conversation import Conversation, Message
from app.models.user import User
from app.schemas.chat import (
    ConversationCreate,
    ConversationList,
    ConversationResponse,
    ConversationUpdate,
    MessageList,
    MessageResponse,
    MessageSend,
    StreamChunk,
)
from app.services.ai import ChatMessage, get_ai_provider

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _get_user_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Conversation:
    """Fetch a conversation owned by the user, or raise 404."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if conv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


async def _count_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> int:
    """Count messages in a conversation."""
    result = await db.execute(
        select(sa_func.count(Message.id)).where(
            Message.conversation_id == conversation_id
        )
    )
    return result.scalar() or 0


def _conv_to_response(conv: Conversation, msg_count: int = 0) -> ConversationResponse:
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        model=conv.model,
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        message_count=msg_count,
    )


# ── Conversation CRUD ────────────────────────────────────────────────────────


@router.get(
    "/chat/conversations",
    response_model=ConversationList,
    summary="List user's conversations",
    description="Return all conversations for the current user, newest first.",
)
async def list_conversations(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ConversationList:
    """List all conversations for the current user."""
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.user_id == current_user.id,
            Conversation.is_archived == False,  # noqa: E712
        )
        .order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
    )
    conversations = list(result.scalars().all())

    # Build responses with message counts
    responses = []
    for conv in conversations:
        count = await _count_messages(db, conv.id)
        responses.append(_conv_to_response(conv, count))

    return ConversationList(conversations=responses, total=len(responses))


@router.post(
    "/chat/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a conversation",
    description="Create a new conversation. Title is optional — auto-generated on first message.",
)
async def create_conversation(
    body: ConversationCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ConversationResponse:
    """Create a new conversation."""
    conv = Conversation(
        user_id=current_user.id,
        title=body.title or None,
        model=body.model or "gpt-4o",
    )
    db.add(conv)
    await db.flush()
    return _conv_to_response(conv)


@router.put(
    "/chat/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Update a conversation",
    description="Update conversation title or archive status.",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ConversationUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> ConversationResponse:
    """Update a conversation (rename, archive)."""
    conv = await _get_user_conversation(db, conversation_id, current_user.id)

    if body.title is not None:
        conv.title = body.title
    if body.is_archived is not None:
        conv.is_archived = body.is_archived

    await db.flush()
    msg_count = await _count_messages(db, conv.id)
    return _conv_to_response(conv, msg_count)


@router.delete(
    "/chat/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
    description="Permanently delete a conversation and all its messages.",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a conversation (cascades to messages)."""
    conv = await _get_user_conversation(db, conversation_id, current_user.id)
    await db.delete(conv)


# ── Messages ─────────────────────────────────────────────────────────────────


@router.get(
    "/chat/conversations/{conversation_id}/messages",
    response_model=MessageList,
    summary="List messages",
    description="Return all messages in a conversation, oldest first.",
)
async def list_messages(
    conversation_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> MessageList:
    """List messages in a conversation (ownership-gated)."""
    await _get_user_conversation(db, conversation_id, current_user.id)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = list(result.scalars().all())

    return MessageList(
        messages=[MessageResponse.model_validate(m) for m in messages],
        total=len(messages),
    )


@router.post(
    "/chat/conversations/{conversation_id}/messages",
    summary="Send a message and stream the AI response",
    description=(
        "Save the user message, then stream the AI response as SSE "
        "(Server-Sent Events). Each event is a JSON ``StreamChunk``."
    ),
)
async def send_message(
    conversation_id: uuid.UUID,
    body: MessageSend,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Send a message and stream the AI response via SSE."""
    conv = await _get_user_conversation(db, conversation_id, current_user.id)

    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=body.content,
    )
    db.add(user_msg)
    await db.flush()

    # Build message history for the AI
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )
    history = list(result.scalars().all())

    ai_messages: list[ChatMessage] = []
    for msg in history:
        ai_messages.append(ChatMessage(role=msg.role, content=msg.content))

    model = body.model or conv.model
    provider = get_ai_provider()

    async def event_stream() -> AsyncGenerator[str, None]:
        """SSE event generator."""
        full_response: list[str] = []

        try:
            async for event in provider.stream_chat(ai_messages, model=model):
                if event.finish_reason:
                    # Save the assistant message
                    assistant_msg = Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content="".join(full_response),
                        model=model,
                        input_tokens=event.input_tokens,
                        output_tokens=event.output_tokens,
                    )
                    db.add(assistant_msg)

                    # Auto-generate title on first response
                    if not conv.title:
                        try:
                            conv.title = await provider.generate_title(
                                body.content, model=model
                            )
                        except Exception:
                            conv.title = "New Chat"

                    await db.flush()

                    # Done event
                    done_chunk = StreamChunk(
                        type="done",
                        finish_reason=event.finish_reason,
                        message_id=str(assistant_msg.id),
                        input_tokens=event.input_tokens,
                        output_tokens=event.output_tokens,
                    )
                    yield f"data: {done_chunk.model_dump_json()}\n\n"
                elif event.content:
                    full_response.append(event.content)
                    chunk = StreamChunk(type="chunk", content=event.content)
                    yield f"data: {chunk.model_dump_json()}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as exc:
            error_chunk = StreamChunk(
                type="error",
                content=str(exc) if str(exc) else "AI service error",
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
