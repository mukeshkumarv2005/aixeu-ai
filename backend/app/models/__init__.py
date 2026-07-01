"""SQLAlchemy ORM models — re-exports for Alembic and application code."""

from app.models.base import Base
from app.models.conversation import Conversation, Message
from app.models.document import DocumentAnalysis, DocumentChunk, DocumentMetadata
from app.models.file import File
from app.models.knowledge import HAS_PGVECTOR, KnowledgeBase, KnowledgeBaseDocument
from app.models.refresh_token import RefreshToken
from app.models.user import User

# Conditionally export DocumentEmbedding (depends on pgvector availability)
if HAS_PGVECTOR:
    from app.models.knowledge import DocumentEmbedding  # noqa: F811

__all__ = [
    "Base",
    "Conversation",
    "DocumentAnalysis",
    "DocumentChunk",
    "DocumentEmbedding",
    "DocumentMetadata",
    "File",
    "KnowledgeBase",
    "KnowledgeBaseDocument",
    "Message",
    "RefreshToken",
    "User",
]
