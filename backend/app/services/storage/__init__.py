"""Storage provider package — local filesystem and S3-compatible backends.

Usage::

    provider = get_storage_provider()
    url = await provider.upload("file.txt", data, "text/plain")
"""

from __future__ import annotations

from app.core.config import settings

from .base import StorageProvider


def get_storage_provider() -> StorageProvider:
    """Return the configured storage provider.

    If ``STORAGE_S3_BUCKET`` is set (non-empty), returns an S3-compatible
    provider stub (which raises ``NotImplementedError`` on all operations
    — implement before using in production).

    Otherwise returns the local-filesystem provider.
    """
    if settings.STORAGE_S3_BUCKET:
        from .s3 import S3StorageProvider

        return S3StorageProvider()

    from .local import LocalStorageProvider

    return LocalStorageProvider()


__all__ = ["StorageProvider", "get_storage_provider"]
