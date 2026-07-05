"""Unit tests for the EmbeddingPipeline."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.knowledge import DocumentEmbedding, KnowledgeBase, KnowledgeBaseDocument
from app.services.embeddings.pipeline import EmbeddingPipeline
from tests.conftest import create_user


@pytest.fixture
async def sample_kb(db_session) -> KnowledgeBase:
    user = await create_user(db_session)
    kb = KnowledgeBase(
        user_id=user.id,
        name="Test KB",
        embedding_model="mock",
    )
    db_session.add(kb)
    await db_session.commit()
    await db_session.refresh(kb)
    return kb


@pytest.fixture
async def sample_document(db_session, sample_kb) -> KnowledgeBaseDocument:
    doc = KnowledgeBaseDocument(
        knowledge_base_id=sample_kb.id,
        title="Sample Doc",
        content="This is some sample text that is long enough to be chunked. We want to test the full processing loop.",
        status="pending",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest.mark.asyncio
async def test_process_document_success(db_session, sample_document):
    pipeline = EmbeddingPipeline(db_session)
    doc = await pipeline.process_document(sample_document.id, chunk_size=100, chunk_overlap=20)

    assert doc.status == "completed"
    assert doc.chunk_count > 0
    assert doc.error_message is None

    # Check that embeddings are persisted in the database
    result = await db_session.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.kb_document_id == sample_document.id)
    )
    embeddings = result.scalars().all()
    assert len(embeddings) == doc.chunk_count
    for emb in embeddings:
        assert emb.content is not None
        assert len(emb.embedding) == 1536
        assert all(v == 0.0 for v in emb.embedding)


@pytest.mark.asyncio
async def test_process_document_empty_content(db_session, sample_document):
    sample_document.content = ""
    await db_session.commit()

    pipeline = EmbeddingPipeline(db_session)
    doc = await pipeline.process_document(sample_document.id)

    assert doc.status == "completed"
    assert doc.chunk_count == 0

    result = await db_session.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.kb_document_id == sample_document.id)
    )
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_process_document_nonexistent_raises(db_session):
    pipeline = EmbeddingPipeline(db_session)
    with pytest.raises(ValueError, match="not found"):
        await pipeline.process_document(UUID(int=0))


@pytest.mark.asyncio
async def test_process_document_no_pgvector_raises(db_session, sample_document):
    pipeline = EmbeddingPipeline(db_session)
    with patch("app.services.embeddings.pipeline.HAS_PGVECTOR", False):
        with pytest.raises(ValueError, match="pgvector extension is not available"):
            await pipeline.process_document(sample_document.id)


@pytest.mark.asyncio
async def test_process_document_already_completed_skipped(db_session, sample_document):
    sample_document.status = "completed"
    sample_document.chunk_count = 12
    await db_session.commit()

    pipeline = EmbeddingPipeline(db_session)
    doc = await pipeline.process_document(sample_document.id)
    assert doc.status == "completed"
    assert doc.chunk_count == 12  # Unchanged


@pytest.mark.asyncio
async def test_process_document_force_reprocess(db_session, sample_document):
    # Process once
    pipeline = EmbeddingPipeline(db_session)
    await pipeline.process_document(sample_document.id)

    # Process again with force=True
    doc = await pipeline.process_document(sample_document.id, force=True)
    assert doc.status == "completed"

    result = await db_session.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.kb_document_id == sample_document.id)
    )
    assert len(result.scalars().all()) > 0


@pytest.mark.asyncio
async def test_process_document_failure(db_session, sample_document):
    pipeline = EmbeddingPipeline(db_session)
    
    # Mock embedder to throw exception
    with patch.object(pipeline._embedder, "generate_embeddings", side_effect=Exception("Embedding failed")):
        doc = await pipeline.process_document(sample_document.id)
        assert doc.status == "failed"
        assert "Embedding failed" in doc.error_message


@pytest.mark.asyncio
async def test_process_knowledge_base_success(db_session, sample_kb, sample_document):
    # Add a second document
    doc2 = KnowledgeBaseDocument(
        knowledge_base_id=sample_kb.id,
        title="Sample Doc 2",
        content="Second document content to verify batch processing logic.",
        status="pending",
    )
    db_session.add(doc2)
    await db_session.commit()

    pipeline = EmbeddingPipeline(db_session)
    processed = await pipeline.process_knowledge_base(sample_kb.id, batch_limit=2)

    assert len(processed) == 2
    assert processed[0].status == "completed"
    assert processed[1].status == "completed"


@pytest.mark.asyncio
async def test_process_knowledge_base_no_pgvector_raises(db_session, sample_kb):
    pipeline = EmbeddingPipeline(db_session)
    with patch("app.services.embeddings.pipeline.HAS_PGVECTOR", False):
        with pytest.raises(ValueError, match="pgvector is not available"):
            await pipeline.process_knowledge_base(sample_kb.id)


@pytest.mark.asyncio
async def test_delete_embeddings(db_session, sample_document):
    pipeline = EmbeddingPipeline(db_session)
    await pipeline.process_document(sample_document.id)

    # Verify they exist
    result = await db_session.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.kb_document_id == sample_document.id)
    )
    assert len(result.scalars().all()) > 0

    # Delete
    await pipeline.delete_embeddings(sample_document.id)

    # Verify deleted
    result = await db_session.execute(
        select(DocumentEmbedding).where(DocumentEmbedding.kb_document_id == sample_document.id)
    )
    assert len(result.scalars().all()) == 0
