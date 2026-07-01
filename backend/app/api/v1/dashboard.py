"""Dashboard API router.

Provides aggregate dashboard data, usage analytics, and activity
feeds — all ownership-gated to the current user.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_active_user
from app.models.conversation import Conversation, Message
from app.models.file import File
from app.models.knowledge import KnowledgeBase, KnowledgeBaseDocument
from app.models.user import User
from app.models.document import DocumentMetadata
from app.schemas.dashboard import (
    DailyTokenUsage,
    DashboardResponse,
    DashboardStats,
    RecentActivityItem,
    RecentChatItem,
    UsageResponse,
)
from app.schemas.storage import FileInfo

router = APIRouter()


# ─── GET /api/v1/dashboard ──────────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Dashboard aggregate data",
    description=(
        "Return aggregate statistics, recent conversations, recent file "
        "uploads, and a combined activity feed for the current user."
    ),
)
async def get_dashboard(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> DashboardResponse:
    """Return all dashboard data in a single response."""
    user_id = current_user.id

    # ── Aggregate stats ────────────────────────────────────────────────
    stats = await _compute_stats(db, user_id)

    # ── Recent chats (with message counts) ─────────────────────────────
    recent_chats = await _fetch_recent_chats(db, user_id)

    # ── Recent files ───────────────────────────────────────────────────
    result = await db.execute(
        select(File)
        .where(File.user_id == user_id)
        .order_by(File.created_at.desc())
        .limit(5)
    )
    recent_files = [FileInfo.model_validate(f) for f in result.scalars().all()]

    # ── Combined activity feed ─────────────────────────────────────────
    recent_activity = await _build_activity_feed(db, user_id)

    return DashboardResponse(
        stats=stats,
        recent_chats=recent_chats,
        recent_files=recent_files,
        recent_activity=recent_activity,
    )


# ─── GET /api/v1/dashboard/usage ────────────────────────────────────────────


@router.get(
    "/dashboard/usage",
    response_model=UsageResponse,
    summary="Usage analytics",
    description=(
        "Return detailed AI token usage (total and per-day for the last "
        "30 days) plus storage totals."
    ),
)
async def get_usage(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> UsageResponse:
    """Return token-usage and storage stats with a daily breakdown."""
    user_id = current_user.id

    # ── Overall totals ─────────────────────────────────────────────────
    result = await db.execute(
        select(
            sa_func.coalesce(sa_func.sum(Message.input_tokens), 0),
            sa_func.coalesce(sa_func.sum(Message.output_tokens), 0),
            sa_func.count(Message.id),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
            Message.role == "assistant",
        )
    )
    row = result.one()
    total_input = row[0] or 0
    total_output = row[1] or 0
    total_messages = row[2] or 0

    # Conversation count
    result = await db.execute(
        select(sa_func.count(Conversation.id)).where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
    )
    total_convs = result.scalar() or 0

    # Storage totals
    result = await db.execute(
        select(
            sa_func.coalesce(sa_func.sum(File.size_bytes), 0),
            sa_func.count(File.id),
        ).where(File.user_id == user_id)
    )
    row = result.one()
    storage_bytes = row[0] or 0
    storage_files = row[1] or 0

    # ── Daily breakdown (last 30 days) ─────────────────────────────────
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(
            sa_func.date(Message.created_at).label("day"),
            sa_func.coalesce(sa_func.sum(Message.input_tokens), 0),
            sa_func.coalesce(sa_func.sum(Message.output_tokens), 0),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
            Message.created_at >= cutoff,
        )
        .group_by(sa_func.date(Message.created_at))
        .order_by(sa_func.date(Message.created_at))
    )
    daily_usage = [
        DailyTokenUsage(
            date=str(row.day),
            input_tokens=row[1] or 0,
            output_tokens=row[2] or 0,
        )
        for row in result.all()
    ]

    return UsageResponse(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_messages=total_messages,
        total_conversations=total_convs,
        daily_usage=daily_usage,
        storage_total_bytes=storage_bytes,
        storage_total_files=storage_files,
    )


# ─── Internal helpers ───────────────────────────────────────────────────────


async def _compute_stats(db: AsyncSession, user_id: uuid.UUID) -> DashboardStats:
    """Compute the six aggregate stat counters for a user."""
    # Conversations
    result = await db.execute(
        select(sa_func.count(Conversation.id)).where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
    )
    total_convs = result.scalar() or 0

    # Messages
    result = await db.execute(
        select(sa_func.count(Message.id))
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
    )
    total_msgs = result.scalar() or 0

    # Files & storage size
    result = await db.execute(
        select(
            sa_func.count(File.id),
            sa_func.coalesce(sa_func.sum(File.size_bytes), 0),
        ).where(File.user_id == user_id)
    )
    row = result.one()
    total_files = row[0] or 0
    total_storage = row[1] or 0

    # Token counts
    result = await db.execute(
        select(
            sa_func.coalesce(sa_func.sum(Message.input_tokens), 0),
            sa_func.coalesce(sa_func.sum(Message.output_tokens), 0),
        )
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
    )
    row = result.one()
    total_input = row[0] or 0
    total_output = row[1] or 0

    # Documents processed
    result = await db.execute(
        select(sa_func.count(DocumentMetadata.id))
        .select_from(DocumentMetadata)
        .join(File, DocumentMetadata.file_id == File.id)
        .where(File.user_id == user_id)
    )
    total_docs_processed = result.scalar() or 0

    # Knowledge bases
    result = await db.execute(
        select(sa_func.count(KnowledgeBase.id)).where(
            KnowledgeBase.user_id == user_id,
        )
    )
    total_kbs = result.scalar() or 0

    # KB chunks (only count completed documents' chunk_count)
    result = await db.execute(
        select(
            sa_func.coalesce(sa_func.sum(KnowledgeBaseDocument.chunk_count), 0),
        )
        .select_from(KnowledgeBaseDocument)
        .join(
            KnowledgeBase,
            KnowledgeBaseDocument.knowledge_base_id == KnowledgeBase.id,
        )
        .where(
            KnowledgeBase.user_id == user_id,
            KnowledgeBaseDocument.status == "completed",
        )
    )
    total_kb_chunks = result.scalar() or 0

    return DashboardStats(
        total_conversations=total_convs,
        total_messages=total_msgs,
        total_files=total_files,
        total_storage_bytes=total_storage,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_documents_processed=total_docs_processed,
        total_knowledge_bases=total_kbs,
        total_kb_chunks=total_kb_chunks,
    )


async def _fetch_recent_chats(
    db: AsyncSession, user_id: uuid.UUID
) -> list[RecentChatItem]:
    """Return the 10 most recently updated conversations with message counts."""
    # Subquery: message count per conversation
    msg_count_subq = (
        select(
            Message.conversation_id,
            sa_func.count(Message.id).label("cnt"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    result = await db.execute(
        select(Conversation, msg_count_subq.c.cnt)
        .outerjoin(
            msg_count_subq,
            Conversation.id == msg_count_subq.c.conversation_id,
        )
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
        .order_by(
            Conversation.updated_at.desc(),
            Conversation.created_at.desc(),
        )
        .limit(10)
    )

    return [
        RecentChatItem(
            id=conv.id,
            title=conv.title,
            model=conv.model,
            message_count=count or 0,
            updated_at=conv.updated_at,
            created_at=conv.created_at,
        )
        for conv, count in result.all()
    ]


async def _build_activity_feed(
    db: AsyncSession, user_id: uuid.UUID
) -> list[RecentActivityItem]:
    """Combine file uploads and conversation activity into a single feed."""
    items: list[RecentActivityItem] = []

    # File uploads
    result = await db.execute(
        select(File)
        .where(File.user_id == user_id)
        .order_by(File.created_at.desc())
        .limit(10)
    )
    for f in result.scalars().all():
        items.append(
            RecentActivityItem(
                id=f.id,
                type="upload",
                description=f"Uploaded {f.filename}",
                created_at=f.created_at,
            )
        )

    # Conversation activity (title creation / updates)
    result = await db.execute(
        select(Conversation)
        .where(
            Conversation.user_id == user_id,
            Conversation.is_archived == False,
        )
        .order_by(Conversation.updated_at.desc())
        .limit(10)
    )
    for conv in result.scalars().all():
        label = conv.title or "New Chat"
        # Use created_at vs updated_at as a heuristic for activity
        is_new = conv.created_at == conv.updated_at
        description = f"Started \"{label}\"" if is_new else f"Updated \"{label}\""
        items.append(
            RecentActivityItem(
                id=conv.id,
                type="chat",
                description=description,
                created_at=conv.updated_at or conv.created_at,
            )
        )

    # Sort newest-first, cap at 20
    items.sort(key=lambda a: a.created_at, reverse=True)
    return items[:20]
