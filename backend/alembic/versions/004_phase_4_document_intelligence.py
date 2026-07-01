"""Phase 4 — Document intelligence tables.

Creates document_metadata, document_chunks, and document_analysis
tables for the document intelligence pipeline.

Revision ID: 004
Revises: 003
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── document_metadata ──────────────────────────────────────────────────
    op.create_table(
        "document_metadata",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "file_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to files.id (one-to-one)",
        ),
        sa.Column(
            "extracted_text",
            sa.Text(),
            nullable=True,
            comment="Full extracted text content of the document",
        ),
        sa.Column(
            "title",
            sa.String(1024),
            nullable=True,
            comment="Extracted document title",
        ),
        sa.Column(
            "author",
            sa.String(512),
            nullable=True,
            comment="Extracted document author",
        ),
        sa.Column(
            "language",
            sa.String(16),
            nullable=True,
            comment="Detected language code (e.g. en, fr)",
        ),
        sa.Column(
            "language_confidence",
            sa.Float(),
            nullable=True,
            comment="Confidence score for language detection (0-1)",
        ),
        sa.Column(
            "page_count",
            sa.Integer(),
            nullable=True,
            comment="Number of pages (PDF/DOCX)",
        ),
        sa.Column(
            "word_count",
            sa.Integer(),
            nullable=True,
            comment="Total word count",
        ),
        sa.Column(
            "character_count",
            sa.Integer(),
            nullable=True,
            comment="Total character count",
        ),
        sa.Column(
            "document_type",
            sa.String(32),
            nullable=True,
            comment="Detected document type (pdf, docx, text, etc.)",
        ),
        sa.Column(
            "created_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Document creation date from metadata",
        ),
        sa.Column(
            "modified_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Document last-modified date from metadata",
        ),
        sa.Column(
            "processing_time_ms",
            sa.BigInteger(),
            nullable=True,
            comment="Total processing time in milliseconds",
        ),
        sa.Column(
            "ocr_used",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether OCR was used for text extraction",
        ),
        sa.Column(
            "error_message",
            sa.String(1024),
            nullable=True,
            comment="Error message if extraction partially failed",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # PK / FK / constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("file_id", name="uq_document_metadata_file"),
    )
    op.create_index(
        "ix_document_metadata_file_id",
        "document_metadata",
        ["file_id"],
        unique=True,
    )

    # ── document_chunks ────────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "file_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to files.id",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="Zero-based position within the document",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Chunk text content",
        ),
        sa.Column(
            "token_count",
            sa.Integer(),
            nullable=True,
            comment="Approximate token count for this chunk",
        ),
        sa.Column(
            "char_count",
            sa.Integer(),
            nullable=False,
            comment="Character count of this chunk",
        ),
        sa.Column(
            "chunk_type",
            sa.String(32),
            nullable=False,
            comment="Chunking strategy: fixed, paragraph, sentence, recursive",
        ),
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=True,
            comment="Optional JSON metadata about the chunk",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # PK / FK / constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "file_id",
            "chunk_index",
            name="uq_file_chunk_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_file_id",
        "document_chunks",
        ["file_id"],
    )

    # ── document_analysis ──────────────────────────────────────────────────
    op.create_table(
        "document_analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "file_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to files.id (one-to-one)",
        ),
        sa.Column(
            "summary",
            sa.Text(),
            nullable=True,
            comment="AI-generated document summary",
        ),
        sa.Column(
            "keywords",
            sa.Text(),
            nullable=True,
            comment="JSON array of extracted keywords",
        ),
        sa.Column(
            "topics",
            sa.Text(),
            nullable=True,
            comment="JSON array of detected topics",
        ),
        sa.Column(
            "entities",
            sa.Text(),
            nullable=True,
            comment="JSON array of detected named entities",
        ),
        sa.Column(
            "category",
            sa.String(128),
            nullable=True,
            comment="Detected document category",
        ),
        sa.Column(
            "language_confidence",
            sa.Float(),
            nullable=True,
            comment="Language detection confidence from AI analysis",
        ),
        sa.Column(
            "model_used",
            sa.String(128),
            nullable=True,
            comment="AI model used for analysis",
        ),
        sa.Column(
            "analysis_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the AI analysis completed",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # PK / FK / constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("file_id", name="uq_document_analysis_file"),
    )
    op.create_index(
        "ix_document_analysis_file_id",
        "document_analysis",
        ["file_id"],
        unique=True,
    )

    # ── Update files table: add processing_error column, update status default ──
    op.add_column(
        "files",
        sa.Column(
            "processing_error",
            sa.String(1024),
            nullable=True,
            comment="Error message if processing_status is 'failed'",
        ),
    )


def downgrade() -> None:
    op.drop_column("files", "processing_error")
    op.drop_table("document_analysis")
    op.drop_table("document_chunks")
    op.drop_table("document_metadata")
