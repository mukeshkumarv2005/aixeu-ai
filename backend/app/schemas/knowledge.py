"""Pydantic schemas for the Knowledge Base service.

Covers CRUD operations for knowledge bases and their documents,
plus embedding and semantic search result schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Knowledge Base ───────────────────────────────────────────────────────────


class KnowledgeBaseCreate(BaseModel):
    """Request to create a new knowledge base."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable name for this knowledge base",
    )
    description: str | None = Field(
        None,
        max_length=10000,
        description="Optional description of the knowledge base contents",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model identifier (e.g. text-embedding-3-small)",
    )


class KnowledgeBaseUpdate(BaseModel):
    """Request to update an existing knowledge base."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class KnowledgeBaseResponse(BaseModel):
    """Knowledge base read response."""

    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    embedding_model: str
    dimension: int
    document_count: int = 0
    total_chunks: int = 0
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeBaseListResponse(BaseModel):
    """Paginated list of knowledge bases."""

    items: list[KnowledgeBaseResponse]
    total: int


# ── Knowledge Base Document ──────────────────────────────────────────────────


class KnowledgeBaseDocumentCreate(BaseModel):
    """Request to add a document to a knowledge base."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Document title",
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Full text content of the document",
    )
    file_id: UUID | None = Field(
        None,
        description="Optional reference to an uploaded File",
    )
    metadata_json: str | None = Field(
        None,
        description="Optional JSON metadata string",
    )


class KnowledgeBaseDocumentResponse(BaseModel):
    """Knowledge base document read response."""

    id: UUID
    knowledge_base_id: UUID
    file_id: UUID | None = None
    title: str
    content: str
    metadata_json: str | None = None
    status: str
    error_message: str | None = None
    chunk_count: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class KnowledgeBaseDocumentListResponse(BaseModel):
    """Paginated list of documents within a knowledge base."""

    items: list[KnowledgeBaseDocumentResponse]
    total: int


# ── Embedding & Search ───────────────────────────────────────────────────────


class SemanticSearchQuery(BaseModel):
    """Request to perform a semantic search against a knowledge base."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Natural language search query",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of results to return",
    )
    similarity_threshold: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold (0-1)",
    )


class SemanticSearchResult(BaseModel):
    """A single search result from a semantic query."""

    document_id: UUID
    document_title: str
    content: str
    chunk_index: int
    similarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Cosine similarity score",
    )
    metadata_json: str | None = None


class SemanticSearchResponse(BaseModel):
    """Results from a semantic search query."""

    query: str
    results: list[SemanticSearchResult]
    total: int
    embedding_model: str
    search_time_ms: float = 0.0


# ── Processing ───────────────────────────────────────────────────────────────


class DocumentProcessRequest(BaseModel):
    """Request to trigger embedding processing for a KB document."""

    force_reprocess: bool = Field(
        default=False,
        description="If True, re-generate embeddings even if already completed",
    )


class DocumentProcessStatus(BaseModel):
    """Processing status for a KB document."""

    document_id: UUID
    status: str
    error_message: str | None = None
    chunk_count: int | None = None
