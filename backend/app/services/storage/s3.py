"""S3-compatible storage provider stub.

This file documents the contract that a real S3 provider must fulfil.
All methods raise ``NotImplementedError``.

Implementing the full S3 provider requires the ``boto3`` / ``aioboto3``
library and AWS credentials (or compatible environment).  Once
implemented, set ``STORAGE_S3_BUCKET`` in the environment and the
factory in ``__init__.py`` will return this provider.
"""

from __future__ import annotations

from typing import BinaryIO

import structlog

from .base import StorageProvider

logger = structlog.get_logger(__name__)


class S3StorageProvider(StorageProvider):
    """S3-compatible storage backend (stub — not yet implemented)."""

    async def upload(
        self,
        *,
        filename: str,
        data: BinaryIO,
        mime_type: str,
        path: str | None = None,
    ) -> str:
        raise NotImplementedError(
            "S3 storage is not implemented yet. "
            "Set STORAGE_S3_BUCKET='' (or omit it) to use local storage."
        )

    async def download(self, path: str) -> bytes:
        raise NotImplementedError("S3 storage is not implemented yet.")

    async def delete(self, path: str) -> None:
        raise NotImplementedError("S3 storage is not implemented yet.")

    async def url(self, path: str) -> str:
        raise NotImplementedError("S3 storage is not implemented yet.")
