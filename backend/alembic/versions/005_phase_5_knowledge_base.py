"""Phase 5 — Knowledge Base tables.

Creates knowledge_bases, kb_documents, and kb_embeddings tables
for the semantic search / RAG knowledge base system.

The kb_embeddings table uses the pgvector extension's ``vector``
type, enabled via ``CREATE EXTENSION IF NOT EXISTS vector``.

Revision ID: 005
Revises: 004
Create Date: 2026-07-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable pgvector extension ──────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── knowledge_bases ────────────────────────────────────────────────────
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to users.id",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable name for this knowledge base",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional description of the knowledge base contents",
        ),
        sa.Column(
            "embedding_model",
            sa.String(128),
            nullable=False,
            server_default=sa.text("'text-embedding-3-small'"),
            comment="Embedding model used for all vectors in this KB",
        ),
        sa.Column(
            "dimension",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1536"),
            comment="Vector dimension matching the embedding model",
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
        # PK / FK
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_knowledge_bases_user_id",
        "knowledge_bases",
        ["user_id"],
    )

    # ── kb_documents ───────────────────────────────────────────────────────
    op.create_table(
        "kb_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "knowledge_base_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to knowledge_bases.id",
        ),
        sa.Column(
            "file_id",
            sa.Uuid(),
            nullable=True,
            comment="Optional FK to files.id",
        ),
        sa.Column(
            "title",
            sa.String(512),
            nullable=False,
            comment="Document title",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="Full text content of the document",
        ),
        sa.Column(
            "metadata_json",
            sa.Text(),
            nullable=True,
            comment="Optional JSON metadata attached to this document",
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="Processing status: pending, processing, completed, failed",
        ),
        sa.Column(
            "error_message",
            sa.String(1024),
            nullable=True,
            comment="Error message if status is 'failed'",
        ),
        sa.Column(
            "chunk_count",
            sa.Integer(),
            nullable=True,
            comment="Number of chunks this document was split into",
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
        # PK / FK
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["files.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_kb_documents_kb_id",
        "kb_documents",
        ["knowledge_base_id"],
    )
    op.create_index(
        "ix_kb_documents_file_id",
        "kb_documents",
        ["file_id"],
    )

    # ── kb_embeddings ──────────────────────────────────────────────────────
    op.create_table(
        "kb_embeddings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "kb_document_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to kb_documents.id",
        ),
        sa.Column(
            "knowledge_base_id",
            sa.Uuid(),
            nullable=False,
            comment="FK to knowledge_bases.id (denormalised for search perf)",
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
            comment="Zero-based chunk index within the document",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            comment="The text that was embedded",
        ),
        sa.Column(
            "model",
            sa.String(128),
            nullable=False,
            comment="Embedding model used to generate this vector",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # PK / FK
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["kb_document_id"],
            ["kb_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_kb_embeddings_kb_document_id",
        "kb_embeddings",
        ["kb_document_id"],
    )
    op.create_index(
        "ix_kb_embeddings_knowledge_base_id",
        "kb_embeddings",
        ["knowledge_base_id"],
    )

    # Add the pgvector column (cannot be created via standard sa.Column)
    op.execute(
        "ALTER TABLE kb_embeddings ADD COLUMN embedding vector(1536) NOT NULL"
    )

    # HNSW index for fast approximate nearest-neighbour search
    op.execute(
        "CREATE INDEX ix_kb_embeddings_embedding_hnsw "
        "ON kb_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("kb_embeddings")
    op.drop_table("kb_documents")
    op.drop_table("knowledge_bases")
