"""Embedding pipeline — chunks documents and generates vector embeddings.

The ``EmbeddingPipeline`` orchestrates:

1. **Chunking** — splits document content into overlapping chunks using the
   configured chunking strategy (default: recursive).
2. **Embedding** — generates vector embeddings for each chunk via the
   configured ``EmbeddingProvider`` (OpenAI, local, or mock).
3. **Persistence** — saves ``DocumentEmbedding`` records to the database and
   updates the document's processing status.
"""

from __future__ import annotations

import json
import time
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import (
    HAS_PGVECTOR,
    DocumentEmbedding,
    KnowledgeBase,
    KnowledgeBaseDocument,
)
from app.services.document.chunkers import (
    ChunkingConfig,
    ChunkingError,
    get_chunker,
)
from app.services.embeddings import (
    EmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)


class EmbeddingPipeline:
    """Chunks KB documents and generates vector embeddings for semantic search."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._embedder: EmbeddingProvider = get_embedding_provider()

    # ── Public API ──────────────────────────────────────────────────────────

    async def process_document(
        self,
        document_id: UUID,
        *,
        force: bool = False,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        strategy: str = "recursive",
    ) -> KnowledgeBaseDocument:
        """Chunk, embed, and persist embeddings for a single document.

        Args:
            document_id: UUID of the ``KnowledgeBaseDocument`` to process.
            force: If ``True``, re-process even if already completed
                (existing embeddings are deleted first).
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Overlap between consecutive chunks.
            strategy: Chunking strategy name (recursive, paragraph, sentence,
                fixed).

        Returns:
            The updated ``KnowledgeBaseDocument`` with status set to
            ``completed`` or ``failed``.

        Raises:
            ValueError: If the document is not found or pgvector is unavailable.
        """
        if not HAS_PGVECTOR:
            raise ValueError(
                "Cannot process document: pgvector extension is not available. "
                "Install pgvector Python package: pip install pgvector"
            )

        # ── Load document ──────────────────────────────────────────────
        doc = await self._get_document(document_id)
        if doc is None:
            raise ValueError(f"KnowledgeBaseDocument {document_id} not found")

        if doc.status == "completed" and not force:
            return doc

        # Load the parent KB for model / dimension info
        kb = await self._get_knowledge_base(doc.knowledge_base_id)

        # ── Delete existing embeddings if re-processing ────────────────
        if force and doc.status == "completed":
            await self._delete_embeddings(document_id)

        # ── Mark as processing ─────────────────────────────────────────
        doc.status = "processing"
        doc.error_message = None
        await self.db.commit()

        try:
            # ── 1. Chunk ───────────────────────────────────────────────
            chunk_config = ChunkingConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunk_strategy=strategy,
                min_chunk_length=50,
                max_chunk_length=chunk_size * 2,
            )
            chunker = get_chunker(strategy)
            chunks = chunker.chunk(doc.content, chunk_config)

            if not chunks:
                doc.status = "completed"
                doc.chunk_count = 0
                await self.db.commit()
                return doc

            # ── 2. Embed ───────────────────────────────────────────────
            texts = [chunk.content for chunk in chunks]
            model = kb.embedding_model if kb else self._embedder.model_name

            embeddings = await self._embedder.generate_embeddings(
                texts, model=model,
            )

            # ── 3. Persist ─────────────────────────────────────────────
            await self._save_embeddings(
                document_id=document_id,
                kb_id=doc.knowledge_base_id,
                chunks=chunks,
                embeddings=embeddings,
                model=model,
            )

            # ── 4. Update document status ──────────────────────────────
            doc.status = "completed"
            doc.chunk_count = len(chunks)
            await self.db.commit()

        except (ChunkingError, ValueError, Exception) as exc:
            doc.status = "failed"
            doc.error_message = f"{type(exc).__name__}: {exc}"
            await self.db.commit()

        return doc

    async def process_knowledge_base(
        self,
        kb_id: UUID,
        *,
        force: bool = False,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
        strategy: str = "recursive",
        batch_limit: int = 10,
    ) -> list[KnowledgeBaseDocument]:
        """Process all unprocessed (or all, if ``force``) documents in a KB.

        Args:
            kb_id: UUID of the ``KnowledgeBase``.
            force: Re-process already-completed documents.
            chunk_size: Maximum characters per chunk.
            chunk_overlap: Overlap between consecutive chunks.
            strategy: Chunking strategy name.
            batch_limit: Maximum number of documents to process in one call.

        Returns:
            List of processed documents (final status after processing).
        """
        if not HAS_PGVECTOR:
            raise ValueError("pgvector is not available — cannot process documents")

        # Find unprocessed documents
        if force:
            stmt = (
                select(KnowledgeBaseDocument)
                .where(KnowledgeBaseDocument.knowledge_base_id == kb_id)
                .limit(batch_limit)
            )
        else:
            stmt = (
                select(KnowledgeBaseDocument)
                .where(
                    KnowledgeBaseDocument.knowledge_base_id == kb_id,
                    KnowledgeBaseDocument.status.in_(["pending", "failed"]),
                )
                .limit(batch_limit)
            )

        result = await self.db.execute(stmt)
        docs = list(result.scalars().all())

        processed: list[KnowledgeBaseDocument] = []
        for doc in docs:
            processed_doc = await self.process_document(
                doc.id,
                force=force,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                strategy=strategy,
            )
            processed.append(processed_doc)

        return processed

    async def delete_embeddings(self, document_id: UUID) -> None:
        """Delete all ``DocumentEmbedding`` records for a document.

        Intended for cleanup before re-processing.
        """
        stmt = delete(DocumentEmbedding).where(
            DocumentEmbedding.kb_document_id == document_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _get_document(
        self, document_id: UUID
    ) -> KnowledgeBaseDocument | None:
        result = await self.db.execute(
            select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.id == document_id
            )
        )
        return result.scalar_one_or_none()

    async def _get_knowledge_base(
        self, kb_id: UUID
    ) -> KnowledgeBase | None:
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def _delete_embeddings(self, document_id: UUID) -> None:
        stmt = delete(DocumentEmbedding).where(
            DocumentEmbedding.kb_document_id == document_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def _save_embeddings(
        self,
        document_id: UUID,
        kb_id: UUID,
        chunks: list,
        embeddings: list[list[float]],
        model: str,
    ) -> None:
        """Bulk-insert ``DocumentEmbedding`` records.

        Both lists are expected to be parallel — one embedding per chunk.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        records = [
            DocumentEmbedding(
                kb_document_id=document_id,
                knowledge_base_id=kb_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                embedding=embeddings[i],
                model=model,
            )
            for i, chunk in enumerate(chunks)
        ]

        self.db.add_all(records)
        await self.db.commit()
