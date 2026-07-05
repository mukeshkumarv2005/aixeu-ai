import asyncio
import logging
from datetime import datetime, UTC
from sqlalchemy import select, delete

from app.core.config import settings
from app.core.logging import setup_logging
from app.database import AsyncSessionFactory
from app.models.file import File
from app.models.knowledge import KnowledgeBaseDocument
from app.models.refresh_token import RefreshToken
from app.services.document.pipeline import DocumentPipeline
from app.services.embeddings.pipeline import EmbeddingPipeline

setup_logging()
logger = logging.getLogger("aevix.worker")


async def process_queued_files() -> None:
    """Check database for files queued for processing and run ingestion."""
    async with AsyncSessionFactory() as session:
        try:
            stmt = select(File).where(File.processing_status.in_(["queued", "pending"]))
            result = await session.execute(stmt)
            files = result.scalars().all()
            
            for file_record in files:
                logger.info(
                    "Worker processing file",
                    extra={"file_id": str(file_record.id), "filename": file_record.filename},
                )
                pipeline = DocumentPipeline(session)
                # pipeline.process handles status updates and commits internally
                await pipeline.process(file_id=file_record.id, user_id=file_record.user_id)
        except Exception as exc:
            logger.error("Error in process_queued_files loop iteration", exc_info=True)


async def process_pending_kb_documents() -> None:
    """Check database for pending knowledge base documents and generate embeddings."""
    async with AsyncSessionFactory() as session:
        try:
            stmt = select(KnowledgeBaseDocument).where(
                KnowledgeBaseDocument.status.in_(["pending", "queued"])
            )
            result = await session.execute(stmt)
            docs = result.scalars().all()
            
            for doc in docs:
                logger.info(
                    "Worker embedding KB document",
                    extra={"document_id": str(doc.id), "title": doc.title},
                )
                pipeline = EmbeddingPipeline(session)
                # pipeline.process_document updates status and commits internally
                await pipeline.process_document(doc.id, force=True)
        except Exception as exc:
            logger.error("Error in process_pending_kb_documents loop iteration", exc_info=True)


async def run_expired_token_cleanup() -> None:
    """Delete expired refresh tokens from the database."""
    async with AsyncSessionFactory() as session:
        try:
            now = datetime.now(UTC)
            result = await session.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < now)
            )
            await session.commit()
            if result.rowcount > 0:
                logger.info(
                    "Worker cleaned up expired refresh tokens",
                    extra={"count": result.rowcount},
                )
        except Exception as exc:
            logger.error("Error in run_expired_token_cleanup", exc_info=True)


async def main() -> None:
    """Background worker entrypoint loop."""
    logger.info("Aevix background worker started successfully")
    
    cleanup_counter = 0
    # Run cleanup every 60 seconds (12 * 5s)
    cleanup_interval_ticks = 12

    while True:
        try:
            # Process files & embeddings
            await process_queued_files()
            await process_pending_kb_documents()
            
            # Periodic cleanups
            cleanup_counter += 1
            if cleanup_counter >= cleanup_interval_ticks:
                await run_expired_token_cleanup()
                cleanup_counter = 0
                
        except Exception as exc:
            logger.error("Unhandled exception in worker main loop", exc_info=True)
            
        await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker shutting down gracefully...")
