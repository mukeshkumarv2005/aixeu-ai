"""Application-wide exception hierarchy.

All custom exceptions inherit from ``AppException``, which FastAPI can
catch and render as JSON error responses via a registered handler.
"""

from __future__ import annotations


class AppException(Exception):
    """Base application exception with optional HTTP-status code."""

    def __init__(
        self,
        status_code: int = 500,
        detail: str = "Internal server error",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)
