"""Pydantic schemas for the Global Search system.

Covers:
* ``SearchResult`` / ``SearchResponse`` — unified result types.
* ``SearchFilters`` — filter/search request parameters.
* ``SavedSearchResponse`` / ``RecentSearchResponse`` — saved/recent search read models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Unified search result ────────────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single search hit from any entity type."""

    entity_type: str = Field(
        ...,
        description="Entity type: conversation, message, file, kb_document, task",
    )
    entity_id: str = Field(
        ...,
        description="UUID of the matched entity as a string",
    )
    title: str = Field(
        ...,
        description="Human-readable title of the matched entity",
    )
    snippet: str = Field(
        ...,
        description="Relevant text snippet showing the match context",
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized relevance score (0–1)",
    )
    url: str = Field(
        ...,
        description="Front-end route for this entity (e.g. /chat/... or /tasks/...)",
    )
    entity_metadata: dict = Field(
        default_factory=dict,
        description="Entity-type-specific metadata (status, priority, file_type, etc.)",
    )


class SearchResponse(BaseModel):
    """Paginated global search response."""

    query: str = Field(..., description="The original search query")
    results: list[SearchResult] = Field(
        default_factory=list,
        description="Flat list of results sorted by score descending",
    )
    total: int = Field(..., description="Total number of matching results")
    offset: int = Field(default=0, description="Offset used for this page")
    limit: int = Field(default=50, description="Limit used for this page")


# ── Search request filters ───────────────────────────────────────────────────


class SearchFilters(BaseModel):
    """Optional filters to narrow a global search."""

    entity_types: list[str] | None = Field(
        None,
        description="Filter to specific entity types (e.g. ['task', 'file'])",
    )
    status: str | None = Field(
        None,
        description="Filter by status (for tasks)",
    )
    priority: str | None = Field(
        None,
        description="Filter by priority (for tasks)",
    )
    kb_id: str | None = Field(
        None,
        description="Limit search to a specific knowledge base",
    )
    date_from: datetime | None = Field(
        None,
        description="Only include entities created/updated after this date",
    )
    date_to: datetime | None = Field(
        None,
        description="Only include entities created/updated before this date",
    )


# ── Saved search models ──────────────────────────────────────────────────────


class SavedSearchCreate(BaseModel):
    """Request to save a search query."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="The search query text to save",
    )
    filters: dict | None = Field(
        None,
        description="Optional search filters as JSON",
    )


class SavedSearchUpdate(BaseModel):
    """Request to update a saved search."""

    query: str | None = Field(None, min_length=1, max_length=1024)
    filters: dict | None = None


class SavedSearchResponse(BaseModel):
    """A saved / bookmarked search."""

    id: str
    query: str
    filters: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Recent search models ─────────────────────────────────────────────────────


class RecentSearchResponse(BaseModel):
    """A recent search history entry."""

    id: str
    query: str
    searched_at: datetime

    model_config = {"from_attributes": True}
