"""Knowledge Base ORM models.

Represents user-curated knowledge bases with vector embeddings for
semantic search (pgvector).  Each ``KnowledgeBase`` can contain many
documents (``KnowledgeBaseDocument``); each document can have many
vector embeddings (``DocumentEmbedding``).

The ``DocumentEmbedding`` model depends on the pgvector extension and
is only registered when the ``pgvector`` Python package is available,
so that SQLite-based tests can still import the other KB models.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# ── Conditional pgvector support ─────────────────────────────────────────────
try:
    from pgvector.sqlalchemy import Vector as _Vector

    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    _Vector = None  # type: ignore [assignment]


# ── Knowledge Base ────────────────────────────────────────────────────────────


class KnowledgeBase(UUIDMixin, TimestampMixin, Base):
    """A user-curated knowledge base — a collection of documents with
    vector embeddings for semantic search."""

    __tablename__ = "knowledge_bases"

    # ── Ownership ─────────────────────────────────────────────────
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Metadata ──────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name for this knowledge base",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the knowledge base contents",
    )
    embedding_model: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="text-embedding-3-small",
        comment="Embedding model used for all vectors in this KB",
    )
    dimension: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1536,
        comment="Vector dimension matching the embedding model",
    )

    # ── Relationships ─────────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User",
        back_populates="knowledge_bases",
    )
    documents: Mapped[list[KnowledgeBaseDocument]] = relationship(
        "KnowledgeBaseDocument",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        order_by="KnowledgeBaseDocument.created_at.desc()",
    )
    if HAS_PGVECTOR:
        embeddings: Mapped[list[DocumentEmbedding]] = relationship(
            "DocumentEmbedding",
            back_populates="knowledge_base",
            cascade="all, delete-orphan",
        )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBase id={self.id} name={self.name!r} "
            f"model={self.embedding_model!r}>"
        )


# ── Knowledge Base Document ──────────────────────────────────────────────────


class KnowledgeBaseDocument(UUIDMixin, TimestampMixin, Base):
    """A single document within a knowledge base.

    Documents can originate from an uploaded ``File`` (via ``file_id``)
    or be created from raw text.
    """

    __tablename__ = "kb_documents"

    # ── Foreign keys ──────────────────────────────────────────────
    knowledge_base_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Document title",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full text content of the document",
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional JSON metadata attached to this document",
    )

    # ── Processing state ──────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        comment="Processing status: pending, processing, completed, failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        String(1024),
        nullable=True,
        comment="Error message if status is 'failed'",
    )
    chunk_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of chunks this document was split into",
    )

    # ── Relationships ─────────────────────────────────────────────
    knowledge_base: Mapped[KnowledgeBase] = relationship(
        "KnowledgeBase",
        back_populates="documents",
    )
    file: Mapped[File | None] = relationship(
        "File",
        back_populates="kb_documents",
    )
    if HAS_PGVECTOR:
        embeddings: Mapped[list[DocumentEmbedding]] = relationship(
            "DocumentEmbedding",
            back_populates="kb_document",
            cascade="all, delete-orphan",
        )
    tasks: Mapped[list[Task]] = relationship(
        "Task",
        back_populates="kb_document",
    )

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBaseDocument id={self.id} title={self.title!r} "
            f"status={self.status!r}>"
        )


# ── Document Embedding (pgvector) ────────────────────────────────────────────


if HAS_PGVECTOR:

    class DocumentEmbedding(UUIDMixin, Base):
        """A single vector embedding of a document chunk.

        Only registered as an ORM model when the ``pgvector`` Python
        package is installed.  The table definition uses the PostgreSQL
        ``vector`` extension type.
        """

        __tablename__ = "kb_embeddings"

        # ── Foreign keys ──────────────────────────────────────────
        kb_document_id: Mapped[UUID] = mapped_column(
            ForeignKey("kb_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
        knowledge_base_id: Mapped[UUID] = mapped_column(
            ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

        # ── Vector & content ──────────────────────────────────────
        chunk_index: Mapped[int] = mapped_column(
            Integer,
            nullable=False,
            comment="Zero-based chunk index within the document",
        )
        content: Mapped[str] = mapped_column(
            Text,
            nullable=False,
            comment="The text that was embedded",
        )
        embedding: Mapped[_Vector] = mapped_column(
            _Vector(1536),  # type: ignore[arg-type]
            nullable=False,
            comment="pgvector embedding vector",
        )
        model: Mapped[str] = mapped_column(
            String(128),
            nullable=False,
            comment="Embedding model used to generate this vector",
        )

        # ── Created-at (immutable once created) ───────────────────
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )

        # ── Relationships ─────────────────────────────────────────
        kb_document: Mapped[KnowledgeBaseDocument] = relationship(
            "KnowledgeBaseDocument",
            back_populates="embeddings",
        )
        knowledge_base: Mapped[KnowledgeBase] = relationship(
            "KnowledgeBase",
            back_populates="embeddings",
        )

        def __repr__(self) -> str:
            return (
                f"<DocumentEmbedding id={self.id} "
                f"chunk_index={self.chunk_index} model={self.model!r}>"
            )


# ── Late imports (avoid circular dependencies) ───────────────────────────────
from app.models.file import File  # noqa: E402, F811
from app.models.task import Task  # noqa: E402, F811
from app.models.user import User  # noqa: E402, F811
