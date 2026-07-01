"""Document intelligence models: metadata, chunks, and AI analysis.

Each uploaded ``File`` can have at most one ``DocumentMetadata`` record,
zero or more ``DocumentChunk`` records, and at most one
``DocumentAnalysis`` record.  The lifecycle is managed by the document
processing pipeline.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class DocumentMetadata(UUIDMixin, TimestampMixin, Base):
    """Extracted text and metadata for a processed document."""

    __tablename__ = "document_metadata"

    # ── Link to File (one-to-one) ─────────────────────────────────
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Extracted text content ────────────────────────────────────
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full extracted text content of the document",
    )

    # ── Bibliographic metadata ────────────────────────────────────
    title: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Extracted document title",
    )
    author: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment="Extracted document author",
    )
    language: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="Detected language code (e.g. en, fr)",
    )
    language_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Confidence score for language detection (0-1)",
    )
    page_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of pages (PDF/DOCX)",
    )
    word_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total word count",
    )
    character_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total character count",
    )
    document_type: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        comment="Detected document type (pdf, docx, text, etc.)",
    )

    # ── Date metadata ─────────────────────────────────────────────
    created_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Document creation date from metadata",
    )
    modified_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Document last-modified date from metadata",
    )

    # ── Processing info ───────────────────────────────────────────
    processing_time_ms: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
        comment="Total processing time in milliseconds",
    )
    ocr_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether OCR was used for text extraction",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Error message if extraction partially failed",
    )

    # ── Relationships ─────────────────────────────────────────────
    file: Mapped[File] = relationship(
        "File",
        back_populates="document_metadata",
        foreign_keys=[file_id],
    )

    def __repr__(self) -> str:
        return f"<DocumentMetadata file_id={self.file_id} title={self.title!r}>"


class DocumentChunk(UUIDMixin, TimestampMixin, Base):
    """A single chunk of a processed document's text."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "file_id", "chunk_index", name="uq_file_chunk_index"
        ),
    )

    # ── Link to File ──────────────────────────────────────────────
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Chunk content ─────────────────────────────────────────────
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Zero-based position within the document",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chunk text content",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Approximate token count for this chunk",
    )
    char_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Character count of this chunk",
    )
    chunk_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Chunking strategy: fixed, paragraph, sentence, recursive",
    )

    # ── Optional metadata (JSON) ──────────────────────────────────
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional JSON metadata about the chunk",
    )

    # ── Relationships ─────────────────────────────────────────────
    file: Mapped[File] = relationship(
        "File",
        back_populates="document_chunks",
        foreign_keys=[file_id],
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk file_id={self.file_id} "
            f"index={self.chunk_index} type={self.chunk_type!r}>"
        )


class DocumentAnalysis(UUIDMixin, TimestampMixin, Base):
    """AI-generated analysis of a document (summary, keywords, etc.)."""

    __tablename__ = "document_analysis"

    # ── Link to File (one-to-one) ─────────────────────────────────
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ─── AI-generated content ─────────────────────────────────────
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated document summary",
    )
    keywords: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of extracted keywords",
    )
    topics: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of detected topics",
    )
    entities: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="JSON array of detected named entities",
    )
    category: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="Detected document category",
    )
    language_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Language detection confidence from AI analysis",
    )

    # ── Processing metadata ───────────────────────────────────────
    model_used: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="AI model used for analysis",
    )
    analysis_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the AI analysis completed",
    )

    # ── Relationships ─────────────────────────────────────────────
    file: Mapped[File] = relationship(
        "File",
        back_populates="document_analysis",
        foreign_keys=[file_id],
    )

    def __repr__(self) -> str:
        return f"<DocumentAnalysis file_id={self.file_id} category={self.category!r}>"


# Avoid circular imports
from app.models.file import File  # noqa: E402, F811
