"""Pydantic schemas for the file-storage service."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FileUploadResponse(BaseModel):
    """Response returned after a successful file upload."""

    id: UUID = Field(
        ...,
        description="Unique file identifier.",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )
    filename: str = Field(
        ...,
        description="Original uploaded filename.",
        json_schema_extra={"example": "report.pdf"},
    )
    mime_type: str = Field(
        ...,
        description="MIME type of the file.",
        json_schema_extra={"example": "application/pdf"},
    )
    size_bytes: int = Field(
        ...,
        description="File size in bytes.",
        json_schema_extra={"example": 245760},
    )
    storage_path: str = Field(
        ...,
        description="Internal storage path for the file.",
        json_schema_extra={"example": "a1b2c3d4e5f6_report.pdf"},
    )
    checksum: str | None = Field(
        None,
        description="SHA-256 hex digest of file content.",
        json_schema_extra={"example": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"},
    )
    created_at: datetime = Field(
        ...,
        description="Upload timestamp.",
        json_schema_extra={"example": "2026-07-01T12:00:00Z"},
    )


class FileInfo(BaseModel):
    """Detailed file metadata (returned by GET /storage/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Unique file identifier.",
        json_schema_extra={"example": "123e4567-e89b-12d3-a456-426614174000"},
    )
    filename: str = Field(
        ...,
        description="Original filename.",
        json_schema_extra={"example": "report.pdf"},
    )
    mime_type: str = Field(
        ...,
        description="MIME type.",
        json_schema_extra={"example": "application/pdf"},
    )
    size_bytes: int = Field(
        ...,
        description="File size in bytes.",
        json_schema_extra={"example": 245760},
    )
    storage_path: str = Field(
        ...,
        description="Internal storage path.",
        json_schema_extra={"example": "a1b2c3d4e5f6_report.pdf"},
    )
    checksum: str | None = Field(
        None,
        description="SHA-256 hex digest of file content.",
        json_schema_extra={"example": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"},
    )
    processing_status: str = Field(
        "completed",
        description="Processing status: pending, processing, completed, failed.",
        json_schema_extra={"example": "completed"},
    )
    is_temporary: bool = Field(
        ...,
        description="Whether the file is marked as temporary.",
        json_schema_extra={"example": False},
    )
    created_at: datetime = Field(
        ...,
        description="Upload timestamp.",
        json_schema_extra={"example": "2026-07-01T12:00:00Z"},
    )
    updated_at: datetime | None = Field(
        None,
        description="Last modification timestamp.",
        json_schema_extra={"example": "2026-07-01T14:30:00Z"},
    )


class FileUpdate(BaseModel):
    """Schema for updating file metadata (PATCH /storage/{id})."""

    filename: str | None = Field(
        None,
        description="New filename for the file.",
        json_schema_extra={"example": "renamed-report.pdf"},
    )


class FileInfoList(BaseModel):
    """Paginated list of files belonging to a user."""

    files: list[FileInfo] = Field(
        ...,
        description="List of file records.",
    )
    total: int = Field(
        ...,
        description="Total number of files.",
        json_schema_extra={"example": 42},
    )
