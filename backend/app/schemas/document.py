"""Pydantic schemas for the document intelligence service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentMetadataResponse(BaseModel):
    """Extracted metadata and text for a processed document."""

    id: UUID
    file_id: UUID
    extracted_text: str | None = None
    title: str | None = None
    author: str | None = None
    language: str | None = None
    language_confidence: float | None = None
    page_count: int | None = None
    word_count: int | None = None
    character_count: int | None = None
    document_type: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None
    processing_time_ms: int | None = None
    ocr_used: bool = False
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentChunkResponse(BaseModel):
    """A single chunk of a processed document."""

    id: UUID
    file_id: UUID
    chunk_index: int
    content: str
    token_count: int | None = None
    char_count: int
    chunk_type: str
    metadata_json: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentChunkListResponse(BaseModel):
    """List of chunks for a document."""

    chunks: list[DocumentChunkResponse]
    total: int
    chunk_type: str
    total_tokens: int = 0


class DocumentAnalysisResponse(BaseModel):
    """AI-generated analysis of a document."""

    id: UUID
    file_id: UUID
    summary: str | None = None
    keywords: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    category: str | None = None
    language_confidence: float | None = None
    model_used: str | None = None
    analysis_completed_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DocumentStatusResponse(BaseModel):
    """Processing status for a document."""

    file_id: UUID
    filename: str
    processing_status: str
    processing_error: str | None = None
    has_metadata: bool = False
    has_analysis: bool = False
    has_chunks: bool = False
    chunk_count: int = 0


class DocumentProcessRequest(BaseModel):
    """Request to (re)process a document."""

    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Target chunk size in characters",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=2000,
        description="Overlap between consecutive chunks in characters",
    )
    chunk_strategy: str = Field(
        default="recursive",
        description="Chunking strategy: fixed, paragraph, sentence, recursive",
    )
    min_chunk_length: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="Minimum chunk length in characters",
    )
    max_chunk_length: int = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Maximum chunk length in characters",
    )
    force_reprocess: bool = Field(
        default=False,
        description="If True, re-process even if already completed",
    )
