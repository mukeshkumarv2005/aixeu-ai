"""RAG service — context builder for knowledge-base-augmented chat.

The ``RAGContextBuilder`` retrieves relevant chunks from a knowledge base
via semantic (vector) search, and formats them into a prompt context that
can be injected into an AI chat conversation.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import HAS_PGVECTOR, KnowledgeBase
from app.services.embeddings import EmbeddingProvider, get_embedding_provider


# ── Data types ──────────────────────────────────────────────────────────────


@dataclass
class RAGSource:
    """A single source chunk used in a RAG context."""

    document_id: uuid.UUID
    document_title: str
    content: str
    chunk_index: int
    similarity: float


@dataclass
class RAGContext:
    """The result of a RAG retrieval — formatted context text plus source info."""

    query: str
    sources: list[RAGSource]
    context_text: str
    kb_name: str
    embedding_model: str


# ── Builder ─────────────────────────────────────────────────────────────────


class RAGContextBuilder:
    """Builds RAG contexts by retrieving KB chunks and formatting for LLM use.

    Typical usage::

        builder = RAGContextBuilder(db)
        context = await builder.build_context("What is X?", kb_id)
        # Use context.context_text as a system prompt, or
        messages = await builder.build_chat_messages("What is X?", kb_id, history)

    Requires the ``pgvector`` extension to be installed.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self._embedder = embedder or get_embedding_provider()

    # ── Public API ──────────────────────────────────────────────────────────

    async def build_context(
        self,
        query: str,
        kb_id: uuid.UUID,
        *,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
    ) -> RAGContext:
        """Retrieve relevant chunks from a KB and build a RAG context string.

        Args:
            query: The user's natural-language query.
            kb_id: UUID of the knowledge base to search against.
            top_k: Maximum number of chunks to retrieve.
            similarity_threshold: Minimum cosine similarity (0–1); 0 means no filter.

        Returns:
            A ``RAGContext`` containing the formatted context text and source
            metadata.

        Raises:
            ValueError: If pgvector is not installed or the KB is not found.
        """
        if not HAS_PGVECTOR:
            raise ValueError(
                "RAG requires the pgvector extension. "
                "Install with: pip install pgvector"
            )

        # Load KB to get embedding model info
        kb = await self._get_kb(kb_id)

        # Generate embedding for the user query
        query_embedding = await self._embedder.generate_embeddings(
            [query], model=kb.embedding_model
        )
        query_vec = query_embedding[0]

        # Vector similarity search
        sources = await self._search(
            kb_id=kb_id,
            query_vec=query_vec,
            top_k=top_k,
            threshold=similarity_threshold,
        )

        # Format as a context string suitable for a system prompt
        context_text = self._format_context(sources)

        return RAGContext(
            query=query,
            sources=sources,
            context_text=context_text,
            kb_name=kb.name,
            embedding_model=kb.embedding_model,
        )

    async def build_chat_messages(
        self,
        query: str,
        kb_id: uuid.UUID,
        history: Sequence,
        *,
        top_k: int = 5,
        similarity_threshold: float = 0.0,
        inject_at_start: bool = True,
    ) -> list:
        """Build a message list with RAG context injected for AI chat.

        This is a convenience wrapper around ``build_context`` that produces a
        ``list[ChatMessage]`` ready to pass to ``AIProvider.stream_chat()``.

        Args:
            query: The user's question.
            kb_id: The knowledge base to search.
            history: Previous conversation messages (list of ``ChatMessage``
                or anything with ``.role`` and ``.content``).
            top_k: Number of chunks to retrieve.
            similarity_threshold: Minimum similarity score.
            inject_at_start: If ``True`` (default), the system context is
                prepended at position 0. If ``False``, it is inserted just
                before the last user message.

        Returns:
            A new message list with the RAG context injected as a system
            message.
        """
        from app.services.ai import ChatMessage

        context = await self.build_context(
            query,
            kb_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        system_msg = ChatMessage(role="system", content=context.context_text)

        result = list(history)

        if inject_at_start:
            result.insert(0, system_msg)
        else:
            # Insert before the last user message
            for i in range(len(result) - 1, -1, -1):
                if result[i].role == "user":
                    result.insert(i, system_msg)
                    break
            else:
                result.append(system_msg)

        return result

    # ── Internal helpers ─────────────────────────────────────────────────────

    async def _get_kb(self, kb_id: uuid.UUID) -> KnowledgeBase:
        result = await self.db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            raise ValueError(f"Knowledge base {kb_id} not found")
        return kb

    async def _search(
        self,
        kb_id: uuid.UUID,
        query_vec: list[float],
        top_k: int,
        threshold: float,
    ) -> list[RAGSource]:
        """Execute the pgvector cosine-similarity search."""
        sql = text(
            """
            SELECT
                e.kb_document_id,
                e.chunk_index,
                e.content,
                d.title,
                1 - (e.embedding <=> :query_vec::vector) AS similarity
            FROM kb_embeddings e
            JOIN kb_documents d ON d.id = e.kb_document_id
            WHERE e.knowledge_base_id = :kb_id
              AND 1 - (e.embedding <=> :query_vec::vector) >= :threshold
            ORDER BY similarity DESC
            LIMIT :top_k
            """
        )

        rows = await self.db.execute(
            sql,
            {
                "query_vec": str(query_vec),
                "kb_id": str(kb_id),
                "threshold": threshold,
                "top_k": top_k,
            },
        )
        results = rows.fetchall()

        return [
            RAGSource(
                document_id=row.kb_document_id,
                document_title=row.title,
                content=row.content,
                chunk_index=row.chunk_index,
                similarity=float(row.similarity),
            )
            for row in results
        ]

    @staticmethod
    def _format_context(sources: list[RAGSource]) -> str:
        """Format retrieved chunks into a system-prompt-ready context string."""
        if not sources:
            return (
                "The knowledge base returned no relevant results for the "
                "user's query. Answer based on your general knowledge, but "
                "note that no specific documents were found."
            )

        parts: list[str] = [
            "You are a helpful assistant with access to a knowledge base. "
            "Use the following retrieved documents to answer the user's "
            "question. If the documents don't contain the answer, say so — "
            "do not make up information.",
            "",
            "---",
        ]

        for i, src in enumerate(sources, 1):
            parts.extend(
                [
                    f"[Source {i}] {src.document_title} "
                    f"(relevance: {src.similarity:.2f})",
                    src.content,
                    "",
                ]
            )

        parts.append("---")
        return "\n".join(parts).strip()
