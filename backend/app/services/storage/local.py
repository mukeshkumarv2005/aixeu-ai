"""Local-filesystem implementation of ``StorageProvider``.

Files are written to a configurable directory on the local filesystem
(``STORAGE_UPLOAD_DIR``).  Subdirectories are created automatically
based on the upload path parameter.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO

import structlog

from app.core.config import settings

from .base import StorageProvider

logger = structlog.get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """Store files on the local filesystem."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(
            base_dir or settings.STORAGE_UPLOAD_DIR
        ).resolve()

    def _resolve(self, path: str) -> Path:
        """Return the absolute filesystem path, preventing traversal attacks."""
        # Resolve the full path and ensure it stays within base_dir
        full_path = (self._base_dir / path).resolve()
        if not str(full_path).startswith(str(self._base_dir)):
            raise PermissionError(f"Path traversal detected: {path}")
        return full_path

    async def upload(
        self,
        *,
        filename: str,
        data: BinaryIO,
        mime_type: str,  # noqa: ARG002 (used by S3 provider)
        path: str | None = None,
    ) -> str:
        """Write *data* to ``{base_dir}/{subdir}/{stored_name}``.

        The stored filename is a hash of the content + original name so
        duplicates can be detected and named consistently.
        """
        content = data.read()

        # Build a content-addressable filename
        raw_hash = hashlib.sha256(content).hexdigest()[:16]
        _, ext = os.path.splitext(filename)
        stored_name = f"{raw_hash}{ext}"

        if path:
            subdir = path.strip("/")
            storage_key = f"{subdir}/{stored_name}"
        else:
            storage_key = stored_name

        dest = self._resolve(storage_key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        dest.write_bytes(content)
        logger.debug("File stored", path=str(dest), size=len(content))
        return storage_key

    async def download(self, path: str) -> bytes:
        """Read and return raw bytes from the local path."""
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"Storage path not found: {path}")
        return full_path.read_bytes()

    async def delete(self, path: str) -> None:
        """Remove the file at *path*."""
        full_path = self._resolve(path)
        if not full_path.exists():
            raise FileNotFoundError(f"Storage path not found: {path}")
        full_path.unlink()
        logger.debug("File deleted", path=str(full_path))

    async def url(self, path: str) -> str:
        """Return the absolute filesystem path as a ``file://`` URL."""
        return str(self._resolve(path))
