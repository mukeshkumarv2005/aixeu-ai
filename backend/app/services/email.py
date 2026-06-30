"""Email sender abstraction and stub implementation.

In development the stub ``ConsoleEmailSender`` logs messages to the
console.  Replace it with a real SMTP-based sender in production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class EmailSender(ABC):
    """Abstract email-sending interface."""

    @abstractmethod
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> None:
        """Deliver an email."""


class ConsoleEmailSender(EmailSender):
    """Stub email sender that logs to the console.

    In development the verification / reset links are printed here.
    """

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> None:
        logger.info(
            "📧  Email would be sent",
            to=to,
            subject=subject,
            body_preview=body[:200],
        )


def get_email_sender() -> EmailSender:
    """Return the configured email sender.

    Currently returns the console stub.  Swap the implementation
    here when integrating a real SMTP provider.
    """
    return ConsoleEmailSender()
