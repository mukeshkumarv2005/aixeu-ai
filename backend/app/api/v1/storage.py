"""File-storage API router.

Provides upload, download, list, and delete operations for user-owned
files.  All file I/O goes through the ``StorageProvider`` abstraction.
"""

from __future__ import annotations

import io
import uuid
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import DbSession, get_current_active_user
from app.core.config import settings
from app.models.file import File
from app.models.user import User
from app.schemas.storage import FileInfo, FileInfoList, FileUploadResponse
from app.services.storage import get_storage_provider

router = APIRouter()


@router.post(
    "/storage/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description=(
        "Upload a file belonging to the current user.  The file body is "
        "sent as ``multipart/form-data``.  Returns metadata about the "
        "stored file including its unique ID.  Maximum file size is "
        "controlled by ``STORAGE_MAX_SIZE_MB``."
    ),
)
async def upload_file(
    file: UploadFile,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> FileUploadResponse:
    """Upload a file and persist its metadata."""
    # ── Validate file ──────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    content = await file.read()
    if len(content) > settings.STORAGE_MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"File exceeds maximum size of "
                f"{settings.STORAGE_MAX_SIZE_MB} MB"
            ),
        )

    # ── Store via provider ─────────────────────────────────────────
    data = io.BytesIO(content)
    provider = get_storage_provider()
    storage_path = await provider.upload(
        filename=file.filename,
        data=data,
        mime_type=file.content_type or "application/octet-stream",
        path=str(current_user.id),
    )

    # ── Persist metadata ───────────────────────────────────────────
    file_record = File(
        user_id=current_user.id,
        filename=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        storage_path=storage_path,
    )
    db.add(file_record)
    await db.flush()

    return FileUploadResponse(
        id=file_record.id,
        filename=file_record.filename,
        mime_type=file_record.mime_type,
        size_bytes=file_record.size_bytes,
        storage_path=file_record.storage_path,
        created_at=file_record.created_at,
    )


@router.get(
    "/storage/files",
    response_model=FileInfoList,
    summary="List user's files",
    description=(
        "Return a list of file metadata records owned by the current "
        "user, ordered by upload date (newest first)."
    ),
)
async def list_files(
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> FileInfoList:
    """List all files for the current user."""
    result = await db.execute(
        select(File)
        .where(File.user_id == current_user.id)
        .order_by(File.created_at.desc(), File.id.desc())
    )
    records = result.scalars().all()
    return FileInfoList(
        files=[FileInfo.model_validate(r) for r in records],
        total=len(records),
    )


@router.get(
    "/storage/{file_id}",
    response_model=FileInfo,
    summary="Get file metadata",
    description="Return metadata for a single file by its UUID.",
)
async def get_file(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> FileInfo:
    """Get file metadata (ownership-gated — 404 for other users)."""
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    return FileInfo.model_validate(record)


@router.get(
    "/storage/{file_id}/download",
    response_class=Response,
    summary="Download a file",
    description=(
        "Stream the file binary.  Ownership-gated — returns 404 "
        "for another user's file."
    ),
)
async def download_file(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Download the raw bytes of a user-owned file."""
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    provider = get_storage_provider()
    try:
        content = await provider.download(record.storage_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File data not found on storage backend",
        )

    return Response(
        content=content,
        media_type=record.mime_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{record.filename}"'
            ),
            "Content-Length": str(record.size_bytes),
        },
    )


@router.delete(
    "/storage/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description=(
        "Delete the file record and its underlying storage object. "
        "Ownership-gated — returns 404 for another user's file."
    ),
)
async def delete_file(
    file_id: uuid.UUID,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a user-owned file (both metadata and storage object)."""
    result = await db.execute(
        select(File).where(
            File.id == file_id,
            File.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    provider = get_storage_provider()
    try:
        await provider.delete(record.storage_path)
    except FileNotFoundError:
        # Storage object is already gone — still delete the record
        pass

    await db.delete(record)
