"""Knowledge Base API router.

Provides CRUD endpoints for knowledge bases and their documents,
plus semantic search against vector embeddings.

All endpoints are ownership-gated (user can only access their own KBs).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_active_user
from app.models.knowledge import HAS_PGVECTOR, KnowledgeBase, KnowledgeBaseDocument
from app.models.user import User
from app.schemas.knowledge import (
    DocumentProcessRequest,
    DocumentProcessStatus,
    KnowledgeBaseCreate,
    KnowledgeBaseDocumentCreate,
    KnowledgeBaseDocumentListResponse,
    KnowledgeBaseDocumentResponse,
    KnowledgeBaseListResponse,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
    SemanticSearchQuery,
    SemanticSearchResponse,
)
from app.services.embeddings import get_embedding_pipeline, get_embedding_provider

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _get_user_kb(
    kb_id: uuid.UUID,
    db: AsyncSession,
    user: User,
) -> KnowledgeBase:
    """Fetch a KB record owned by the user, raising 404 if not found."""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return record


async def _get_kb_document(
    document_id: uuid.UUID,
    kb_id: uuid.UUID,
    db: AsyncSession,
) -> KnowledgeBaseDocument:
    """Fetch a KB document, raising 404 if not found."""
    result = await db.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.id == document_id,
            KnowledgeBaseDocument.knowledge_base_id == kb_id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return record


async def _count_documents(kb_id: uuid.UUID, db: AsyncSession) -> int:
    """Count documents in a KB."""
    result = await db.execute(
        select(func.count(KnowledgeBaseDocument.id)).where(
            KnowledgeBaseDocument.knowledge_base_id == kb_id,
        )
    )
    return result.scalar() or 0


async def _kb_to_response(
    kb: KnowledgeBase, db: AsyncSession
) -> KnowledgeBaseResponse:
    """Convert a KB model to a response (with computed counts)."""
    doc_count = await _count_documents(kb.id, db)
    # Sum chunk counts from documents
    chunk_result = await db.execute(
        select(func.coalesce(func.sum(KnowledgeBaseDocument.chunk_count), 0)).where(
            KnowledgeBaseDocument.knowledge_base_id == kb.id,
        )
    )
    total_chunks = chunk_result.scalar() or 0
    return KnowledgeBaseResponse(
        id=kb.id,
        user_id=kb.user_id,
        name=kb.name,
        description=kb.description,
        embedding_model=kb.embedding_model,
        dimension=kb.dimension,
        document_count=doc_count,
        total_chunks=total_chunks,
        created_at=kb.created_at,
        updated_at=kb.updated_at,
    )


# ── Knowledge Base CRUD ─────────────────────────────────────────────────────


@router.post(
    "/knowledge-bases",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge base",
)
async def create_knowledge_base(
    body: KnowledgeBaseCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeBaseResponse:
    """Create a new knowledge base for the authenticated user."""
    kb = KnowledgeBase(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        embedding_model=body.embedding_model,
        dimension=(
            1536
            if "text-embedding-3" in body.embedding_model
            else get_embedding_provider().dimension
        ),
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return await _kb_to_response(kb, db)


@router.get(
    "/knowledge-bases",
    response_model=KnowledgeBaseListResponse,
    summary="List knowledge bases",
)
async def list_knowledge_bases(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> KnowledgeBaseListResponse:
    """List all knowledge bases for the authenticated user."""
    # Build query to fetch KnowledgeBase and aggregates in a single join query
    stmt = (
        select(
            KnowledgeBase,
            func.count(KnowledgeBaseDocument.id).label("doc_count"),
            func.coalesce(func.sum(KnowledgeBaseDocument.chunk_count), 0).label("total_chunks")
        )
        .outerjoin(KnowledgeBaseDocument, KnowledgeBase.id == KnowledgeBaseDocument.knowledge_base_id)
        .where(KnowledgeBase.user_id == current_user.id)
        .group_by(KnowledgeBase.id)
        .order_by(KnowledgeBase.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    items = [
        KnowledgeBaseResponse(
            id=kb.id,
            user_id=kb.user_id,
            name=kb.name,
            description=kb.description,
            embedding_model=kb.embedding_model,
            dimension=kb.dimension,
            document_count=doc_count,
            total_chunks=total_chunks,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
        )
        for kb, doc_count, total_chunks in rows
    ]

    count_result = await db.execute(
        select(func.count(KnowledgeBase.id)).where(
            KnowledgeBase.user_id == current_user.id
        )
    )
    total = count_result.scalar() or 0

    return KnowledgeBaseListResponse(items=items, total=total)


@router.get(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Get a knowledge base",
)
async def get_knowledge_base(
    kb_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeBaseResponse:
    """Get a single knowledge base by ID."""
    kb = await _get_user_kb(kb_id, db, current_user)
    return await _kb_to_response(kb, db)


@router.patch(
    "/knowledge-bases/{kb_id}",
    response_model=KnowledgeBaseResponse,
    summary="Update a knowledge base",
)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    body: KnowledgeBaseUpdate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeBaseResponse:
    """Update a knowledge base's metadata."""
    kb = await _get_user_kb(kb_id, db, current_user)

    if body.name is not None:
        kb.name = body.name
    if body.description is not None:
        kb.description = body.description

    await db.commit()
    await db.refresh(kb)
    return await _kb_to_response(kb, db)


@router.delete(
    "/knowledge-bases/{kb_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge base",
)
async def delete_knowledge_base(
    kb_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a knowledge base and all its documents and embeddings."""
    kb = await _get_user_kb(kb_id, db, current_user)
    await db.delete(kb)
    await db.commit()


# ── Document CRUD ───────────────────────────────────────────────────────────


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=KnowledgeBaseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a document to a knowledge base",
)
async def add_kb_document(
    kb_id: uuid.UUID,
    body: KnowledgeBaseDocumentCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeBaseDocumentResponse:
    """Add a new document to a knowledge base."""
    await _get_user_kb(kb_id, db, current_user)

    doc = KnowledgeBaseDocument(
        knowledge_base_id=kb_id,
        file_id=body.file_id,
        title=body.title,
        content=body.content,
        metadata_json=body.metadata_json,
        status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    return KnowledgeBaseDocumentResponse.model_validate(doc)


@router.get(
    "/knowledge-bases/{kb_id}/documents",
    response_model=KnowledgeBaseDocumentListResponse,
    summary="List documents in a knowledge base",
)
async def list_kb_documents(
    kb_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> KnowledgeBaseDocumentListResponse:
    """List documents in a knowledge base with pagination."""
    await _get_user_kb(kb_id, db, current_user)

    count_result = await db.execute(
        select(func.count(KnowledgeBaseDocument.id)).where(
            KnowledgeBaseDocument.knowledge_base_id == kb_id,
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(KnowledgeBaseDocument)
        .where(KnowledgeBaseDocument.knowledge_base_id == kb_id)
        .order_by(KnowledgeBaseDocument.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    docs = result.scalars().all()

    return KnowledgeBaseDocumentListResponse(
        items=[KnowledgeBaseDocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    response_model=KnowledgeBaseDocumentResponse,
    summary="Get a KB document",
)
async def get_kb_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> KnowledgeBaseDocumentResponse:
    """Get a single document from a knowledge base."""
    await _get_user_kb(kb_id, db, current_user)
    doc = await _get_kb_document(doc_id, kb_id, db)
    return KnowledgeBaseDocumentResponse.model_validate(doc)


@router.delete(
    "/knowledge-bases/{kb_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a KB document",
)
async def delete_kb_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a document from a knowledge base (embeddings cascade)."""
    await _get_user_kb(kb_id, db, current_user)
    doc = await _get_kb_document(doc_id, kb_id, db)
    await db.delete(doc)
    await db.commit()


# ── Document Processing ─────────────────────────────────────────────────────


@router.post(
    "/knowledge-bases/{kb_id}/documents/{doc_id}/process",
    response_model=DocumentProcessStatus,
    summary="Process a KB document (chunk + embed)",
)
async def process_kb_document(
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    body: DocumentProcessRequest | None = None,
) -> DocumentProcessStatus:
    """Trigger embedding processing for a KB document."""
    await _get_user_kb(kb_id, db, current_user)
    doc = await _get_kb_document(doc_id, kb_id, db)

    if settings.ASYNC_WORKERS:
        doc.status = "pending"
        doc.error_message = None
        await db.commit()
        await db.refresh(doc)
        return DocumentProcessStatus(
            document_id=doc.id,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=doc.chunk_count,
        )

    pipeline = get_embedding_pipeline(db)
    force = body.force_reprocess if body else False

    updated = await pipeline.process_document(doc.id, force=force)

    return DocumentProcessStatus(
        document_id=updated.id,
        status=updated.status,
        error_message=updated.error_message,
        chunk_count=updated.chunk_count,
    )


@router.post(
    "/knowledge-bases/{kb_id}/process",
    response_model=list[DocumentProcessStatus],
    summary="Process all pending KB documents",
)
async def process_knowledge_base(
    kb_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    force: bool = Query(default=False),
) -> list[DocumentProcessStatus]:
    """Process all pending (or all, if force) documents in a KB."""
    await _get_user_kb(kb_id, db, current_user)

    if settings.ASYNC_WORKERS:
        stmt = update(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.knowledge_base_id == kb_id
        )
        if not force:
            stmt = stmt.where(KnowledgeBaseDocument.status.in_(["pending", "failed"]))
        stmt = stmt.values(status="pending", error_message=None)
        await db.execute(stmt)
        await db.commit()

        stmt_select = select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.knowledge_base_id == kb_id
        )
        if not force:
            stmt_select = stmt_select.where(KnowledgeBaseDocument.status == "pending")
        result = await db.execute(stmt_select)
        processed = result.scalars().all()

        return [
            DocumentProcessStatus(
                document_id=doc.id,
                status=doc.status,
                error_message=doc.error_message,
                chunk_count=doc.chunk_count,
            )
            for doc in processed
        ]

    pipeline = get_embedding_pipeline(db)
    processed = await pipeline.process_knowledge_base(kb_id, force=force)

    return [
        DocumentProcessStatus(
            document_id=doc.id,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=doc.chunk_count,
        )
        for doc in processed
    ]


# ── Semantic Search ─────────────────────────────────────────────────────────


@router.post(
    "/knowledge-bases/{kb_id}/search",
    response_model=SemanticSearchResponse,
    summary="Semantic search against a knowledge base",
)
async def semantic_search(
    kb_id: uuid.UUID,
    query: SemanticSearchQuery,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> SemanticSearchResponse:
    """Perform semantic (vector) search across a knowledge base.

    This endpoint searches over vector embeddings using pgvector's
    cosine-similarity operator (``<=>``). It requires the pgvector
    extension to be installed.
    """
    kb = await _get_user_kb(kb_id, db, current_user)

    if not HAS_PGVECTOR:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Semantic search requires the pgvector extension",
        )

    import time

    start = time.monotonic()

    # Generate the query embedding
    embedder = get_embedding_provider()
    query_embedding = await embedder.generate_embeddings(
        [query.query], model=kb.embedding_model
    )
    query_vec = query_embedding[0]

    # Perform cosine-similarity search via raw SQL (pgvector-specific)
    #   embedding <=> :query_vec  → cosine distance (0 = identical, 2 = opposite)
    #   We convert to similarity: 1 - distance
    from sqlalchemy import text

    similarity_threshold = query.similarity_threshold or 0.0
    top_k = query.top_k

    sql = text(
        """
        SELECT
            e.id,
            e.kb_document_id,
            e.chunk_index,
            e.content,
            e.model,
            d.title,
            d.metadata_json,
            1 - (e.embedding <=> :query_vec::vector) AS similarity
        FROM kb_embeddings e
        JOIN kb_documents d ON d.id = e.kb_document_id
        WHERE e.knowledge_base_id = :kb_id
          AND 1 - (e.embedding <=> :query_vec::vector) >= :threshold
        ORDER BY similarity DESC
        LIMIT :top_k
        """
    )

    result = await db.execute(
        sql,
        {
            "query_vec": str(query_vec),
            "kb_id": str(kb.id),
            "threshold": similarity_threshold,
            "top_k": top_k,
        },
    )
    rows = result.fetchall()

    search_results = [
        {
            "document_id": row.kb_document_id,
            "document_title": row.title,
            "content": row.content,
            "chunk_index": row.chunk_index,
            "similarity": float(row.similarity),
            "metadata_json": row.metadata_json,
        }
        for row in rows
    ]

    elapsed_ms = (time.monotonic() - start) * 1000

    return SemanticSearchResponse(
        query=query.query,
        results=search_results,
        total=len(search_results),
        embedding_model=kb.embedding_model,
        search_time_ms=round(elapsed_ms, 2),
    )
