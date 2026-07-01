"""Document processing pipeline — orchestrates extraction, chunking, and analysis.

The ``DocumentPipeline`` class coordinates the full lifecycle:

1. Read file from storage
2. Extract text (via the appropriate extractor)
3. Extract metadata (title, author, language, counts, dates)
4. Chunk the extracted text (configurable strategy)
5. AI analysis (summary, keywords, topics, entities, category)
6. Persist all results to the database
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import DocumentAnalysis, DocumentChunk, DocumentMetadata
from app.models.file import File as FileModel
from app.schemas.document import DocumentProcessRequest
from app.services.document.analyzer import (
    AIAnalyzer,
    AnalysisError,
    AnalysisResult,
    get_ai_analyzer,
)
from app.services.document.chunkers import (
    Chunk,
    ChunkingConfig,
    ChunkingError,
    get_chunker,
)
from app.services.document.extractors import (
    ExtractResult,
    ExtractionError,
    get_extractor,
)
from app.services.storage import get_storage_provider


class DocumentPipeline:
    """Orchestrates the end-to-end document processing pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._storage = get_storage_provider()

    async def process(
        self,
        file_id: UUID,
        user_id: UUID,
        params: DocumentProcessRequest | None = None,
    ) -> FileModel:
        """Run the full processing pipeline on a file.

        Args:
            file_id: The UUID of the file to process.
            user_id: The UUID of the owning user.
            params: Optional processing parameters (chunk size, strategy, etc.).

        Returns:
            The updated ``FileModel`` with processing_status set to ``completed``
            or ``failed``.

        Raises:
            ValueError: If the file is not found or does not belong to the user.
        """
        # ── Load the file record ──────────────────────────────────────────
        result = await self.db.execute(
            select(FileModel).where(
                FileModel.id == file_id,
                FileModel.user_id == user_id,
            )
        )
        file_record = result.scalar_one_or_none()
        if file_record is None:
            raise ValueError(f"File {file_id} not found for user {user_id}")

        params = params or DocumentProcessRequest()

        # If already processed and not forced, skip
        if (
            file_record.processing_status == "completed"
            and not params.force_reprocess
        ):
            return file_record

        # ── Mark as processing ────────────────────────────────────────────
        file_record.processing_status = "processing"
        file_record.processing_error = None
        await self.db.commit()

        try:
            # ── Step 1: Download file from storage ────────────────────────
            storage_path = file_record.storage_path
            local_path = await self._download_file(storage_path)

            # ── Step 2: Extract text ──────────────────────────────────────
            extractor = get_extractor(file_record.mime_type)
            extract_result = await extractor.extract(
                local_path, file_record.mime_type
            )
            extracted_text = extract_result.text

            # ── Step 3: Extract metadata ──────────────────────────────────
            metadata_record = await self._extract_and_save_metadata(
                file_record=file_record,
                extracted_text=extracted_text,
                extract_result=extract_result,
            )

            # ── Step 4: Delete old chunks if re-processing ────────────────
            if params.force_reprocess:
                old_chunks = await self.db.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.file_id == file_id
                    )
                )
                for chunk in old_chunks.scalars().all():
                    await self.db.delete(chunk)
                await self.db.commit()

            # ── Step 5: Chunk the text ────────────────────────────────────
            chunker_config = ChunkingConfig(
                chunk_size=params.chunk_size,
                chunk_overlap=params.chunk_overlap,
                chunk_strategy=params.chunk_strategy,
                min_chunk_length=params.min_chunk_length,
                max_chunk_length=params.max_chunk_length,
            )
            chunker = get_chunker(params.chunk_strategy)
            chunks = chunker.chunk(extracted_text, chunker_config)
            await self._save_chunks(file_id, chunks)

            # ── Step 6: AI Analysis ──────────────────────────────────────
            analyzer = get_ai_analyzer()
            metadata_dict = {}
            if metadata_record:
                metadata_dict = {
                    "title": metadata_record.title,
                    "author": metadata_record.author,
                    "language": metadata_record.language,
                    "document_type": metadata_record.document_type,
                }
            analysis = await analyzer.analyze(
                extracted_text, metadata=metadata_dict
            )
            await self._save_analysis(file_id, analysis)

            # ── Mark as completed ─────────────────────────────────────────
            file_record.processing_status = "completed"
            await self.db.commit()

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            file_record.processing_status = "failed"
            file_record.processing_error = error_msg[:1024]
            await self.db.commit()

        return file_record

    async def _download_file(self, storage_path: str) -> str:
        """Download a file from storage to a temp location."""
        from app.core.config import settings

        temp_dir = Path(settings.STORAGE_UPLOAD_DIR) / "_processing"
        temp_dir.mkdir(parents=True, exist_ok=True)

        local_path = str(temp_dir / Path(storage_path).name)
        data = await self._storage.download(path=storage_path)
        Path(local_path).write_bytes(data)
        return local_path

    async def _extract_and_save_metadata(
        self,
        file_record: FileModel,
        extracted_text: str,
        extract_result: ExtractResult,
    ) -> DocumentMetadata:
        """Extract document metadata and persist to DB."""
        from app.services.document.metadata_extractor import extract_metadata

        # Delete existing metadata if re-processing
        if file_record.document_metadata:
            await self.db.delete(file_record.document_metadata)
            await self.db.commit()

        meta = extract_metadata(
            text=extracted_text,
            filename=file_record.filename,
            mime_type=file_record.mime_type,
            page_count=extract_result.page_count,
            ocr_used=extract_result.ocr_used,
            error_message=extract_result.error_message,
        )

        metadata_record = DocumentMetadata(
            file_id=file_record.id,
            extracted_text=extracted_text,
            title=meta.get("title"),
            author=meta.get("author"),
            language=meta.get("language"),
            language_confidence=meta.get("language_confidence"),
            page_count=meta.get("page_count"),
            word_count=meta.get("word_count"),
            character_count=meta.get("character_count"),
            document_type=meta.get("document_type"),
            created_date=meta.get("created_date"),
            modified_date=meta.get("modified_date"),
            processing_time_ms=meta.get("processing_time_ms"),
            ocr_used=meta.get("ocr_used", False),
            error_message=meta.get("error_message"),
        )
        self.db.add(metadata_record)
        await self.db.commit()
        return metadata_record

    async def _save_chunks(
        self, file_id: UUID, chunks: list[Chunk]
    ) -> None:
        """Persist chunk records to the database."""
        for chunk in chunks:
            db_chunk = DocumentChunk(
                file_id=file_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                token_count=chunk.token_count,
                char_count=chunk.char_count,
                chunk_type=chunk.chunk_type,
                metadata_json=json.dumps(chunk.metadata)
                if chunk.metadata
                else None,
            )
            self.db.add(db_chunk)

        await self.db.commit()

    async def _save_analysis(
        self,
        file_id: UUID,
        analysis_result: AnalysisResult,
    ) -> DocumentAnalysis:
        """Persist AI analysis results to the database."""
        # Delete existing analysis if re-processing
        old_result = await self.db.execute(
            select(DocumentAnalysis).where(
                DocumentAnalysis.file_id == file_id
            )
        )
        for old in old_result.scalars().all():
            await self.db.delete(old)
        await self.db.commit()

        analysis_record = DocumentAnalysis(
            file_id=file_id,
            summary=analysis_result.summary,
            keywords=json.dumps(analysis_result.keywords)
            if analysis_result.keywords
            else None,
            topics=json.dumps(analysis_result.topics)
            if analysis_result.topics
            else None,
            entities=json.dumps(analysis_result.entities)
            if analysis_result.entities
            else None,
            category=analysis_result.category,
            language_confidence=analysis_result.language_confidence,
            model_used=analysis_result.model_used,
            analysis_completed_at=datetime.now(timezone.utc),
        )
        self.db.add(analysis_record)
        await self.db.commit()
        return analysis_record
