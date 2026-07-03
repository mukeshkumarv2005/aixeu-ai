"""Global Search service — unified hybrid search across all entity types.

The ``GlobalSearchService`` combines full-text (ILIKE) and semantic (vector)
search to find results across:
* Conversations (title)
* Messages (content)
* Files (filename, extracted text)
* Knowledge-base documents (title, content)
* Tasks (title, description)

Results are scored on a normalised 0–1 scale and returned in descending
order, with optional pagination and entity-type filtering.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import Select, delete, or_, select, text, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message
from app.models.file import File
from app.models.knowledge import (
    HAS_PGVECTOR,
    KnowledgeBase,
    KnowledgeBaseDocument,
)
from app.models.task import Task
from app.models.search import RecentSearch, SavedSearch
from app.services.embeddings import EmbeddingProvider, get_embedding_provider
from app.schemas.search import (
    RecentSearchResponse,
    SavedSearchCreate,
    SavedSearchResponse,
    SavedSearchUpdate,
    SearchFilters,
    SearchResult,
    SearchResponse,
)


# ── Data types ──────────────────────────────────────────────────────────────


@dataclass
class _ScoredHit:
    """Internal raw hit before normalisation and response building."""

    entity_type: str
    entity_id: uuid.UUID | str
    title: str
    snippet: str
    score: float  # raw score from the query (may be 0 for FTS fallback)
    url: str
    entity_metadata: dict = field(default_factory=dict)

    def to_result(self, max_score: float) -> SearchResult:
        """Normalise score to 0–1 and return a Pydantic result."""
        normalised = self.score / max_score if max_score > 0 else 0.0
        return SearchResult(
            entity_type=self.entity_type,
            entity_id=str(self.entity_id),
            title=self.title,
            snippet=self.snippet,
            score=round(min(normalised, 1.0), 4),
            url=self.url,
            entity_metadata=self.entity_metadata,
        )


# ── Entity-type URL builders ────────────────────────────────────────────────


def _conversation_url(conv_id: uuid.UUID) -> str:
    return f"/chat/{conv_id}"


def _message_url(msg: Message) -> str:
    return f"/chat/{msg.conversation_id}?message={msg.id}"


def _file_url(file_id: uuid.UUID) -> str:
    return f"/files/{file_id}"


def _kb_doc_url(doc_id: uuid.UUID) -> str:
    return f"/knowledge/documents/{doc_id}"


def _task_url(task_id: uuid.UUID) -> str:
    return f"/tasks/{task_id}"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _or_ilike(column, query: str):
    """ILIKE pattern-matching helper."""
    return column.ilike(f"%{query}%")


def _make_snippet(text: str | None, max_len: int = 200) -> str:
    """Truncate *text* to *max_len* chars, appending ``…`` if trimmed."""
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rsplit(" ", 1)[0] + "…"


# ── Search scoring weights ────────────────────────────────────────────────────

# How much each search modality contributes to the final score.
# These are applied after each modality's internal score is normalised to 0-1.
FTS_WEIGHT = 0.3
VECTOR_WEIGHT = 0.7


# ── Service ──────────────────────────────────────────────────────────────────


class GlobalSearchService:
    """Unified global search across all entity types.

    Usage::

        service = GlobalSearchService(db)
        response = await service.search(user_id, "my query")
    """

    def __init__(
        self,
        db: AsyncSession,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.db = db
        self._embedder = embedder or get_embedding_provider()

    # ── Main search entry point ────────────────────────────────────────────

    async def search(
        self,
        user_id: uuid.UUID,
        query: str,
        *,
        filters: SearchFilters | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SearchResponse:
        """Execute a global hybrid search across all entity types.

        Args:
            user_id: Owning user's UUID (results are scoped to this user).
            query: The search query string.
            filters: Optional entity-type, status, priority, KB, and date filters.
            offset: Pagination offset.
            limit: Maximum results to return (default 50, max 200).

        Returns:
            A ``SearchResponse`` with results sorted by score descending.
        """
        filters = filters or SearchFilters()
        entity_types = filters.entity_types or [
            "message",
            "conversation",
            "file",
            "kb_document",
            "task",
        ]

        # Generate query embedding for vector search (if pgvector available)
        query_vec: list[float] | None = None
        if HAS_PGVECTOR and query.strip():
            try:
                query_vec = (
                    await self._embedder.generate_embeddings([query])
                )[0]
            except Exception:
                query_vec = None  # fall back to FTS-only

        # Run searches in parallel for each entity type
        all_hits: list[_ScoredHit] = []

        if "conversation" in entity_types:
            hits = await self._search_conversations(
                user_id, query, filters, query_vec
            )
            all_hits.extend(hits)

        if "message" in entity_types:
            hits = await self._search_messages(
                user_id, query, filters, query_vec
            )
            all_hits.extend(hits)

        if "file" in entity_types:
            hits = await self._search_files(
                user_id, query, filters, query_vec
            )
            all_hits.extend(hits)

        if "kb_document" in entity_types:
            hits = await self._search_kb_documents(
                user_id, query, filters, query_vec
            )
            all_hits.extend(hits)

        if "task" in entity_types:
            hits = await self._search_tasks(
                user_id, query, filters, query_vec
            )
            all_hits.extend(hits)

        # Sort by raw score descending
        all_hits.sort(key=lambda h: h.score, reverse=True)

        total = len(all_hits)
        page = all_hits[offset : offset + limit]

        # Normalise scores relative to the max score on this page
        max_score = max((h.score for h in page), default=1.0)
        results = [h.to_result(max_score) for h in page]

        return SearchResponse(
            query=query,
            results=results,
            total=total,
            offset=offset,
            limit=limit,
        )

    # ── Per-entity search methods ─────────────────────────────────────────

    async def _search_conversations(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: SearchFilters,
        query_vec: list[float] | None,
    ) -> list[_ScoredHit]:
        """Full-text search on conversation titles."""
        hits: list[_ScoredHit] = []
        stmt = (
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                _or_ilike(Conversation.title, query),
            )
        )
        stmt = self._apply_date_filter(stmt, Conversation, filters)
        result = await self.db.execute(stmt)
        convs = result.scalars().all()

        for conv in convs:
            fts_score = 0.8  # fixed score for FTS matches
            score = fts_score * FTS_WEIGHT
            hits.append(_ScoredHit(
                entity_type="conversation",
                entity_id=conv.id,
                title=conv.title or "Untitled Conversation",
                snippet=conv.title or "",
                score=score,
                url=_conversation_url(conv.id),
                entity_metadata={"is_archived": conv.is_archived},
            ))
        return hits

    async def _search_messages(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: SearchFilters,
        query_vec: list[float] | None,
    ) -> list[_ScoredHit]:
        """Full-text search on message content."""
        hits: list[_ScoredHit] = []
        stmt = (
            select(Message, Conversation.title)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .where(
                Conversation.user_id == user_id,
                _or_ilike(Message.content, query),
            )
            .order_by(Message.created_at.desc())
        )
        stmt = self._apply_date_filter(stmt, Message, filters)
        result = await self.db.execute(stmt)
        rows = result.all()

        for msg, conv_title in rows:
            fts_score = 0.9
            score = fts_score * FTS_WEIGHT
            snippet = _make_snippet(msg.content)
            hits.append(_ScoredHit(
                entity_type="message",
                entity_id=msg.id,
                title=conv_title or "Untitled Conversation",
                snippet=snippet,
                score=score,
                url=_message_url(msg),
                entity_metadata={
                    "role": msg.role,
                    "conversation_id": str(msg.conversation_id),
                },
            ))
        return hits

    async def _search_files(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: SearchFilters,
        query_vec: list[float] | None,
    ) -> list[_ScoredHit]:
        """Search on filename and extracted document text."""
        hits: list[_ScoredHit] = []
        # Files table — search on filename
        stmt = (
            select(File)
            .where(
                File.user_id == user_id,
                _or_ilike(File.filename, query),
            )
            .order_by(File.created_at.desc())
        )
        stmt = self._apply_date_filter(stmt, File, filters)
        result = await self.db.execute(stmt)
        files = result.scalars().all()

        for f in files:
            fts_score = 0.75
            score = fts_score * FTS_WEIGHT
            hits.append(_ScoredHit(
                entity_type="file",
                entity_id=f.id,
                title=f.filename,
                snippet=f.filename,
                score=score,
                url=_file_url(f.id),
                entity_metadata={
                    "mime_type": f.mime_type,
                    "size_bytes": f.size_bytes,
                    "processing_status": f.processing_status,
                },
            ))

        # Also search on extracted text in DocumentMetadata
        from app.models.document import DocumentMetadata

        stmt2 = (
            select(File, DocumentMetadata.extracted_text)
            .join(DocumentMetadata, DocumentMetadata.file_id == File.id)
            .where(
                File.user_id == user_id,
                _or_ilike(DocumentMetadata.extracted_text, query),
            )
            .order_by(File.created_at.desc())
        )
        stmt2 = self._apply_date_filter(stmt2, File, filters)
        result2 = await self.db.execute(stmt2)
        seen_ids = {h.entity_id for h in hits}
        for f, extracted in result2.all():
            if str(f.id) in seen_ids:
                continue
            seen_ids.add(str(f.id))
            fts_score = 0.7
            score = fts_score * FTS_WEIGHT
            snippet = _make_snippet(extracted)
            hits.append(_ScoredHit(
                entity_type="file",
                entity_id=f.id,
                title=f.filename,
                snippet=snippet or f.filename,
                score=score,
                url=_file_url(f.id),
                entity_metadata={
                    "mime_type": f.mime_type,
                    "size_bytes": f.size_bytes,
                    "processing_status": f.processing_status,
                },
            ))

        return hits

    async def _search_kb_documents(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: SearchFilters,
        query_vec: list[float] | None,
    ) -> list[_ScoredHit]:
        """Hybrid search on KB documents: FTS + optional vector search."""
        hits: list[_ScoredHit] = []

        # ── Full-text search on kb_documents ──────────────────────────
        stmt = (
            select(KnowledgeBaseDocument, KnowledgeBase.name)
            .join(KnowledgeBase, KnowledgeBaseDocument.knowledge_base_id == KnowledgeBase.id)
            .where(
                KnowledgeBase.user_id == user_id,
                or_(
                    _or_ilike(KnowledgeBaseDocument.title, query),
                    _or_ilike(KnowledgeBaseDocument.content, query),
                ),
            )
            .order_by(KnowledgeBaseDocument.created_at.desc())
        )
        stmt = self._apply_date_filter(stmt, KnowledgeBaseDocument, filters)

        # Apply kb_id filter if specified
        if filters.kb_id:
            try:
                kb_uuid = uuid.UUID(filters.kb_id)
                stmt = stmt.where(
                    KnowledgeBaseDocument.knowledge_base_id == kb_uuid
                )
            except ValueError:
                pass  # ignore invalid UUID

        result = await self.db.execute(stmt)
        rows = result.all()
        fts_hit_ids: set[str] = set()

        for doc, kb_name in rows:
            fts_hit_ids.add(str(doc.id))
            fts_score = 0.7
            score = fts_score * FTS_WEIGHT
            snippet = _make_snippet(doc.content)
            hits.append(_ScoredHit(
                entity_type="kb_document",
                entity_id=doc.id,
                title=doc.title,
                snippet=snippet,
                score=score,
                url=_kb_doc_url(doc.id),
                entity_metadata={
                    "kb_name": kb_name,
                    "kb_id": str(doc.knowledge_base_id),
                    "status": doc.status,
                },
            ))

        # ── Vector search on kb_documents ────────────────────────────
        if HAS_PGVECTOR and query_vec is not None and query.strip():
            try:
                vector_hits = await self._vector_search_kb_documents(
                    user_id, query, query_vec, filters
                )
                for vh in vector_hits:
                    # If a FTS hit already exists for this doc, boost its score
                    if str(vh.entity_id) in fts_hit_ids:
                        for existing in hits:
                            if str(existing.entity_id) == str(vh.entity_id):
                                existing.score += vh.score * VECTOR_WEIGHT
                                break
                    else:
                        vh.score *= VECTOR_WEIGHT
                        hits.append(vh)
            except Exception:
                pass  # vector search error — FTS results still valid

        return hits

    async def _vector_search_kb_documents(
        self,
        user_id: uuid.UUID,
        query: str,
        query_vec: list[float],
        filters: SearchFilters,
    ) -> list[_ScoredHit]:
        """Vector similarity search on KB documents via pgvector.

        This queries the ``kb_embeddings`` table directly using cosine
        distance (``<=>``), normalised to a 0–1 similarity score.
        """
        filter_clauses = ["kb.user_id = :user_id"]

        params: dict = {
            "user_id": str(user_id),
            "query_vec": str(query_vec),
        }

        if filters.kb_id:
            try:
                kb_uuid = uuid.UUID(filters.kb_id)
                filter_clauses.append("e.knowledge_base_id = :kb_id")
                params["kb_id"] = str(kb_uuid)
            except ValueError:
                pass

        where_clause = " AND ".join(filter_clauses)

        sql = text(f"""
            SELECT
                d.id,
                d.title,
                d.content,
                e.chunk_index,
                kb.name AS kb_name,
                d.knowledge_base_id,
                d.status,
                1 - (e.embedding <=> :query_vec::vector) AS similarity
            FROM kb_embeddings e
            JOIN kb_documents d ON d.id = e.kb_document_id
            JOIN knowledge_bases kb ON kb.id = e.knowledge_base_id
            JOIN users u ON u.id = kb.user_id
            WHERE {where_clause}
              AND 1 - (e.embedding <=> :query_vec::vector) >= 0.0
            ORDER BY similarity DESC
            LIMIT 20
        """)

        rows = await self.db.execute(sql, params)
        results = rows.fetchall()

        scored: dict[str, _ScoredHit] = {}
        for row in results:
            doc_id = str(row.id)
            sim = float(row.similarity)
            if doc_id in scored:
                # Keep the best similarity for each document
                if sim > scored[doc_id].score:
                    scored[doc_id].score = sim
            else:
                scored[doc_id] = _ScoredHit(
                    entity_type="kb_document",
                    entity_id=row.id,
                    title=row.title,
                    snippet=_make_snippet(row.content),
                    score=sim,
                    url=_kb_doc_url(row.id),
                    entity_metadata={
                        "kb_name": row.kb_name,
                        "kb_id": str(row.knowledge_base_id),
                        "status": row.status,
                    },
                )

        return list(scored.values())

    async def _search_tasks(
        self,
        user_id: uuid.UUID,
        query: str,
        filters: SearchFilters,
        query_vec: list[float] | None,
    ) -> list[_ScoredHit]:
        """Full-text search on task title, description, and comments."""
        hits: list[_ScoredHit] = []

        stmt = (
            select(Task)
            .where(
                Task.owner_id == user_id,
                or_(
                    _or_ilike(Task.title, query),
                    _or_ilike(Task.description, query),
                ),
            )
            .order_by(Task.created_at.desc())
        )
        stmt = self._apply_date_filter(stmt, Task, filters)

        # Apply status filter
        if filters.status:
            stmt = stmt.where(Task.status == filters.status)
        if filters.priority:
            stmt = stmt.where(Task.priority == filters.priority)

        result = await self.db.execute(stmt)
        tasks = result.scalars().all()

        for t in tasks:
            fts_score = 0.85
            score = fts_score * FTS_WEIGHT
            snippet = _make_snippet(t.description or t.title)
            hits.append(_ScoredHit(
                entity_type="task",
                entity_id=t.id,
                title=t.title,
                snippet=snippet,
                score=score,
                url=_task_url(t.id),
                entity_metadata={
                    "status": t.status,
                    "priority": t.priority,
                    "due_date": t.due_date.isoformat() if t.due_date else None,
                },
            ))

        return hits

    # ── Date-range filter helper ─────────────────────────────────────────

    def _apply_date_filter(
        self,
        stmt: Select,
        model,
        filters: SearchFilters,
    ) -> Select:
        """Apply ``date_from`` / ``date_to`` filters to a SELECT if present."""
        if filters.date_from:
            if hasattr(model, "created_at"):
                stmt = stmt.where(model.created_at >= filters.date_from)
            elif hasattr(model, "searched_at"):
                stmt = stmt.where(model.searched_at >= filters.date_from)
        if filters.date_to:
            if hasattr(model, "created_at"):
                stmt = stmt.where(model.created_at <= filters.date_to)
            elif hasattr(model, "searched_at"):
                stmt = stmt.where(model.searched_at <= filters.date_to)
        return stmt

    # ── Saved searches ───────────────────────────────────────────────────

    async def save_search(
        self,
        user_id: uuid.UUID,
        data: SavedSearchCreate,
    ) -> SavedSearchResponse:
        """Persist a search query as a saved/bookmarked search."""
        saved = SavedSearch(
            owner_id=user_id,
            query=data.query,
            filters=data.filters,
        )
        self.db.add(saved)
        await self.db.commit()
        await self.db.refresh(saved)
        return SavedSearchResponse(
            id=str(saved.id),
            query=saved.query,
            filters=saved.filters,
            created_at=saved.created_at,
        )

    async def list_saved_searches(
        self,
        user_id: uuid.UUID,
    ) -> list[SavedSearchResponse]:
        """Return all saved searches for the user, newest first."""
        stmt = (
            select(SavedSearch)
            .where(SavedSearch.owner_id == user_id)
            .order_by(SavedSearch.created_at.desc())
        )
        result = await self.db.execute(stmt)
        saved = result.scalars().all()
        return [
            SavedSearchResponse(
                id=str(s.id),
                query=s.query,
                filters=s.filters,
                created_at=s.created_at,
            )
            for s in saved
        ]

    async def update_saved_search(
        self,
        user_id: uuid.UUID,
        search_id: uuid.UUID,
        data: SavedSearchUpdate,
    ) -> SavedSearchResponse:
        """Update a saved search's query and/or filters."""
        stmt = select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.owner_id == user_id,
        )
        result = await self.db.execute(stmt)
        saved = result.scalar_one_or_none()
        if saved is None:
            from app.core.exceptions import AppException
            raise AppException(
                status_code=404,
                detail=f"Saved search {search_id} not found",
            )

        if data.query is not None:
            saved.query = data.query
        if data.filters is not None:
            saved.filters = data.filters
        await self.db.commit()
        await self.db.refresh(saved)
        return SavedSearchResponse(
            id=str(saved.id),
            query=saved.query,
            filters=saved.filters,
            created_at=saved.created_at,
        )

    async def delete_saved_search(
        self,
        user_id: uuid.UUID,
        search_id: uuid.UUID,
    ) -> None:
        """Delete a saved search by ID (owner-gated)."""
        stmt = select(SavedSearch).where(
            SavedSearch.id == search_id,
            SavedSearch.owner_id == user_id,
        )
        result = await self.db.execute(stmt)
        saved = result.scalar_one_or_none()
        if saved is None:
            from app.core.exceptions import AppException
            raise AppException(
                status_code=404,
                detail=f"Saved search {search_id} not found",
            )
        await self.db.delete(saved)
        await self.db.commit()

    # ── Recent searches ──────────────────────────────────────────────────

    async def record_recent_search(
        self,
        user_id: uuid.UUID,
        query: str,
    ) -> RecentSearchResponse:
        """Record a search in the user's recent-search history.

        Automatically prunes old entries when the user exceeds
        ``MAX_RECENT_SEARCHES`` (default 50).
        """
        MAX_RECENT_SEARCHES = 50

        recent = RecentSearch(owner_id=user_id, query=query)
        self.db.add(recent)
        await self.db.commit()
        await self.db.refresh(recent)

        # Prune excess entries (keep the newest MAX_RECENT_SEARCHES)
        count_stmt = select(sa_func.count(RecentSearch.id)).where(
            RecentSearch.owner_id == user_id
        )
        count_result = await self.db.execute(count_stmt)
        count = count_result.scalar_one()

        if count > MAX_RECENT_SEARCHES:
            # Find the cutoff ID and delete older entries
            subq = (
                select(RecentSearch.id)
                .where(RecentSearch.owner_id == user_id)
                .order_by(RecentSearch.searched_at.desc())
                .offset(MAX_RECENT_SEARCHES)
                .limit(1)
            )
            subq_result = await self.db.execute(subq)
            cutoff = subq_result.scalar_one_or_none()
            if cutoff:
                del_stmt = (
                    delete(RecentSearch)
                    .where(
                        RecentSearch.owner_id == user_id,
                        RecentSearch.searched_at <= (
                            select(RecentSearch.searched_at)
                            .where(RecentSearch.id == cutoff)
                            .scalar_subquery()
                        ),
                    )
                )
                await self.db.execute(del_stmt)
                await self.db.commit()

        return RecentSearchResponse(
            id=str(recent.id),
            query=recent.query,
            searched_at=recent.searched_at,
        )

    async def list_recent_searches(
        self,
        user_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[RecentSearchResponse]:
        """Return the user's most recent searches."""
        stmt = (
            select(RecentSearch)
            .where(RecentSearch.owner_id == user_id)
            .order_by(RecentSearch.searched_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        recent = result.scalars().all()
        return [
            RecentSearchResponse(
                id=str(r.id),
                query=r.query,
                searched_at=r.searched_at,
            )
            for r in recent
        ]

    async def clear_recent_searches(
        self,
        user_id: uuid.UUID,
    ) -> None:
        """Clear all recent-search history for the user."""
        stmt = delete(RecentSearch).where(
            RecentSearch.owner_id == user_id
        )
        await self.db.execute(stmt)
        await self.db.commit()
