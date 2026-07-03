"""Global Search API router.

Provides a unified search endpoint that queries across Conversations,
Messages, Files, Knowledge Base, and Tasks, plus CRUD for saved searches
and recent-search history.  All endpoints are ownership-gated via the
``get_current_active_user`` dependency.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import DbSession, get_current_active_user
from app.models.user import User
from app.schemas.search import (
    RecentSearchResponse,
    SavedSearchCreate,
    SavedSearchResponse,
    SavedSearchUpdate,
    SearchFilters,
    SearchResponse,
)
from app.services.search import GlobalSearchService

router = APIRouter()


# ── Global search ─────────────────────────────────────────────────────────────


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Global search",
    description=(
        "Unified search across Conversations, Messages, Files, "
        "Knowledge Base, and Tasks.  Supports full-text and optional "
        "semantic (vector) search.  Results are ownership-gated and "
        "sorted by relevance."
    ),
)
async def global_search(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    q: str = Query(
        ...,
        min_length=1,
        max_length=1024,
        description="The search query string",
    ),
    entity_types: str | None = Query(
        None,
        description=(
            "Comma-separated list of entity types to search. "
            "Options: conversation, message, file, kb_document, task. "
            "Defaults to all types."
        ),
    ),
    status: str | None = Query(
        None,
        description="Filter by status (for tasks)",
    ),
    priority: str | None = Query(
        None,
        description="Filter by priority (for tasks)",
    ),
    kb_id: str | None = Query(
        None,
        description="Limit search to a specific knowledge base (UUID)",
    ),
    date_from: datetime | None = Query(
        None,
        description="Only include entities created/updated after this date (ISO 8601)",
    ),
    date_to: datetime | None = Query(
        None,
        description="Only include entities created/updated before this date (ISO 8601)",
    ),
    offset: int = Query(
        0,
        ge=0,
        le=10000,
        description="Number of results to skip",
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum results to return",
    ),
) -> SearchResponse:
    """Execute a global search across all entity types."""
    service = GlobalSearchService(db)

    # Parse optional comma-separated entity types
    parsed_types: list[str] | None = None
    if entity_types:
        parsed_types = [t.strip() for t in entity_types.split(",") if t.strip()]

    filters = SearchFilters(
        entity_types=parsed_types,
        status=status,
        priority=priority,
        kb_id=kb_id,
        date_from=date_from,
        date_to=date_to,
    )

    return await service.search(
        current_user.id,
        q,
        filters=filters,
        offset=offset,
        limit=limit,
    )


# ── Saved searches ────────────────────────────────────────────────────────────


@router.get(
    "/search/saved",
    response_model=list[SavedSearchResponse],
    summary="List saved searches",
    description=(
        "Return all saved/bookmarked searches for the current user, "
        "ordered newest first."
    ),
)
async def list_saved_searches(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> list[SavedSearchResponse]:
    """List saved searches for the current user."""
    service = GlobalSearchService(db)
    return await service.list_saved_searches(current_user.id)


@router.post(
    "/search/saved",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a search",
    description=(
        "Persist the current search query and optional filters so "
        "the user can re-run it later."
    ),
)
async def save_search(
    body: SavedSearchCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> SavedSearchResponse:
    """Save a search query."""
    service = GlobalSearchService(db)
    return await service.save_search(current_user.id, body)


@router.patch(
    "/search/saved/{search_id}",
    response_model=SavedSearchResponse,
    summary="Update saved search",
    description=(
        "Update a saved search's query and/or filters.  "
        "Ownership-gated — returns 404 for another user's saved search."
    ),
)
async def update_saved_search(
    search_id: uuid.UUID,
    body: SavedSearchUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> SavedSearchResponse:
    """Update a saved search."""
    service = GlobalSearchService(db)
    try:
        return await service.update_saved_search(
            current_user.id, search_id, body
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )


@router.delete(
    "/search/saved/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved search",
    description=(
        "Delete a saved search.  "
        "Ownership-gated — returns 404 for another user's saved search."
    ),
)
async def delete_saved_search(
    search_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a saved search."""
    service = GlobalSearchService(db)
    try:
        await service.delete_saved_search(current_user.id, search_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Saved search {search_id} not found",
        )


# ── Recent searches ───────────────────────────────────────────────────────────


@router.get(
    "/search/recent",
    response_model=list[RecentSearchResponse],
    summary="List recent searches",
    description=(
        "Return the current user's recent search history, "
        "ordered most-recent first (max 20)."
    ),
)
async def list_recent_searches(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> list[RecentSearchResponse]:
    """List recent searches for the current user."""
    service = GlobalSearchService(db)
    return await service.list_recent_searches(current_user.id)


@router.post(
    "/search/recent",
    response_model=RecentSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record recent search",
    description=(
        "Record a search query in the user's recent-search history. "
        "Older entries are auto-pruned when the limit (50) is exceeded."
    ),
)
async def record_recent_search(
    body: dict,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> RecentSearchResponse:
    """Record a search in recent history."""
    query = body.get("query", "")
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required",
        )
    service = GlobalSearchService(db)
    return await service.record_recent_search(current_user.id, query.strip())


@router.delete(
    "/search/recent",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear recent searches",
    description="Clear all recent-search history for the current user.",
)
async def clear_recent_searches(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Clear all recent searches."""
    service = GlobalSearchService(db)
    await service.clear_recent_searches(current_user.id)
