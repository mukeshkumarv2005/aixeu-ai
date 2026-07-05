"""Document intelligence API router.

Provides endpoints to trigger document processing (text extraction,
chunking, AI analysis) and to retrieve the results: metadata, chunks,
and analysis.  All endpoints are ownership-gated.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession, get_current_active_user
from app.models.document import DocumentAnalysis, DocumentChunk, DocumentMetadata
from app.models.file import File
from app.models.user import User
from app.schemas.document import (
    DocumentAnalysisResponse,
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentMetadataResponse,
    DocumentProcessRequest,
    DocumentStatusResponse,
)
from app.services.document.pipeline import DocumentPipeline

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────────


from sqlalchemy.orm import joinedload

async def _get_user_file(
    file_id: uuid.UUID,
    db: AsyncSession,
    user: User,
) -> File:
    """Fetch a file record, raising 404 if not found or not owned by user."""
    result = await db.execute(
        select(File)
        .options(
            joinedload(File.document_metadata),
            joinedload(File.document_analysis),
        )
        .where(
            File.id == file_id,
            File.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return record


# ── Endpoints ───────────────────────────────────────────────────────────────────


@router.post(
    "/documents/{file_id}/process",
    response_model=DocumentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Process a document",
    description=(
        "Run the full document processing pipeline on a file: text "
        "extraction, metadata extraction, chunking, and AI analysis. "
        "Returns the updated processing status.  Accepts optional query "
        "parameters or a JSON body to configure chunking behaviour."
    ),
)
async def process_document(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    body: DocumentProcessRequest | None = None,
) -> DocumentStatusResponse:
    """Trigger (or re-trigger) document processing."""
    file_record = await _get_user_file(file_id, db, current_user)

    if settings.ASYNC_WORKERS:
        file_record.processing_status = "queued"
        file_record.processing_error = None
        
        force = body.force_reprocess if body else False
        if force:
            from app.models.document import DocumentAnalysis, DocumentChunk, DocumentMetadata
            if file_record.document_metadata:
                await db.delete(file_record.document_metadata)
            if file_record.document_analysis:
                await db.delete(file_record.document_analysis)
            # Delete chunks
            from sqlalchemy import delete
            await db.execute(delete(DocumentChunk).where(DocumentChunk.file_id == file_id))

        await db.commit()
        await db.refresh(file_record)
        return await _build_status_response(file_record, db)

    pipeline = DocumentPipeline(db)
    updated = await pipeline.process(
        file_id=file_id,
        user_id=current_user.id,
        params=body,
    )

    return await _build_status_response(updated, db)


@router.get(
    "/documents/{file_id}/status",
    response_model=DocumentStatusResponse,
    summary="Get document processing status",
    description=(
        "Return the current processing status for a file including "
        "whether metadata, chunks, and analysis are available."
    ),
)
async def get_document_status(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> DocumentStatusResponse:
    """Get the processing status of a document."""
    file_record = await _get_user_file(file_id, db, current_user)
    return await _build_status_response(file_record, db)


@router.get(
    "/documents/{file_id}/metadata",
    response_model=DocumentMetadataResponse,
    summary="Get document metadata",
    description=(
        "Return the extracted metadata for a processed document "
        "(title, author, language, word count, etc.).  Returns 404 if "
        "the document has not been processed yet."
    ),
)
async def get_document_metadata(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> DocumentMetadataResponse:
    """Get extracted metadata for a processed document."""
    file_record = await _get_user_file(file_id, db, current_user)

    if file_record.document_metadata is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has not been processed yet",
        )

    return DocumentMetadataResponse.model_validate(
        file_record.document_metadata
    )


@router.get(
    "/documents/{file_id}/chunks",
    response_model=DocumentChunkListResponse,
    summary="Get document chunks",
    description=(
        "Return the text chunks for a processed document, ordered by "
        "chunk index.  Supports pagination via ``offset`` and ``limit`` "
        "query parameters."
    ),
)
async def get_document_chunks(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
    offset: int = Query(default=0, ge=0, description="Number of chunks to skip"),
    limit: int = Query(
        default=50, ge=1, le=200, description="Max chunks to return"
    ),
) -> DocumentChunkListResponse:
    """Get paginated text chunks for a processed document."""
    file_record = await _get_user_file(file_id, db, current_user)

    # Total count
    count_result = await db.execute(
        select(func.count(DocumentChunk.id)).where(
            DocumentChunk.file_id == file_id,
        )
    )
    total = count_result.scalar() or 0

    if total == 0:
        return DocumentChunkListResponse(
            chunks=[], total=0, chunk_type="", total_tokens=0
        )

    # Fetch paginated chunks
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.file_id == file_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    chunks = result.scalars().all()

    # Determine chunk type from the first chunk
    chunk_type = chunks[0].chunk_type if chunks else ""
    total_tokens = sum(c.token_count or 0 for c in chunks)

    return DocumentChunkListResponse(
        chunks=[DocumentChunkResponse.model_validate(c) for c in chunks],
        total=total,
        chunk_type=chunk_type,
        total_tokens=total_tokens,
    )


@router.get(
    "/documents/{file_id}/analysis",
    response_model=DocumentAnalysisResponse,
    summary="Get document AI analysis",
    description=(
        "Return the AI-generated analysis for a processed document "
        "(summary, keywords, topics, entities, category).  Returns 404 "
        "if the document has not been analysed yet."
    ),
)
async def get_document_analysis(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> DocumentAnalysisResponse:
    """Get AI analysis results for a processed document."""
    file_record = await _get_user_file(file_id, db, current_user)

    if file_record.document_analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document has not been analysed yet",
        )

    analysis = file_record.document_analysis

    # Deserialize JSON fields for the response
    import json

    return DocumentAnalysisResponse(
        id=analysis.id,
        file_id=analysis.file_id,
        summary=analysis.summary,
        keywords=json.loads(analysis.keywords) if analysis.keywords else [],
        topics=json.loads(analysis.topics) if analysis.topics else [],
        entities=json.loads(analysis.entities) if analysis.entities else [],
        category=analysis.category,
        language_confidence=analysis.language_confidence,
        model_used=analysis.model_used,
        analysis_completed_at=analysis.analysis_completed_at,
        created_at=analysis.created_at,
    )


# ── Internal helpers ────────────────────────────────────────────────────────────


async def _build_status_response(
    file_record: File,
    db: AsyncSession,
) -> DocumentStatusResponse:
    """Build a status response from a file record."""
    has_metadata = file_record.document_metadata is not None
    has_analysis = file_record.document_analysis is not None

    # Count chunks
    if hasattr(file_record, "document_chunks") and file_record.document_chunks:
        chunk_count = len(file_record.document_chunks)
        has_chunks = chunk_count > 0
    else:
        result = await db.execute(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.file_id == file_record.id,
            )
        )
        chunk_count = result.scalar() or 0
        has_chunks = chunk_count > 0

    return DocumentStatusResponse(
        file_id=file_record.id,
        filename=file_record.filename,
        processing_status=file_record.processing_status,
        processing_error=file_record.processing_error,
        has_metadata=has_metadata,
        has_analysis=has_analysis,
        has_chunks=has_chunks,
        chunk_count=chunk_count,
    )
