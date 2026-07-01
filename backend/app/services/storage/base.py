"""Abstract ``StorageProvider`` interface.

All file I/O in the application goes through this abstraction so the
underlying storage backend (local filesystem, S3, GCS, …) can be swapped
without changing business logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageProvider(ABC):
    """Abstract file-storage interface."""

    @abstractmethod
    async def upload(
        self,
        *,
        filename: str,
        data: BinaryIO,
        mime_type: str,
        path: str | None = None,
    ) -> str:
        """Upload a file and return its storage path / URL.

        Parameters
        ----------
        filename:
            Original filename (used to derive the storage key).
        data:
            Binary file content (seekable).
        mime_type:
            MIME type of the file (e.g. ``image/png``).
        path:
            Optional subdirectory / prefix within the storage root.
            When ``None`` the file is stored at the root.

        Returns
        -------
        str
            The storage path / URL that can later be used with
            ``download``, ``delete``, and ``url``.
        """

    @abstractmethod
    async def download(self, path: str) -> bytes:
        """Return the raw bytes stored at *path*.

        Raises ``FileNotFoundError`` if the path does not exist.
        """

    @abstractmethod
    async def delete(self, path: str) -> None:
        """Delete the file at *path*.

        Raises ``FileNotFoundError`` if the path does not exist.
        """

    @abstractmethod
    async def url(self, path: str) -> str:
        """Return a public URL (or local path) for *path*.

        For local storage this may be a filesystem path or a relative
        URL.  For S3 it would be a signed / public S3 URL.
        """
